import logging
import shutil
import tempfile
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import inngest
import inngest.fast_api
from inngest.experimental import ai
import inngest.experimental.ai.gemini  # required to access ai.gemini
from dotenv import load_dotenv
import uuid
import os
import datetime
from .data_loader import load_and_chunk_pdf, embed_texts
from .vector_db import QdrantStorage
from .custom_types import RAGChunkAndSrc, RAGUpsertResult, RAGSearchResult, RAQQueryResult


load_dotenv()

# Direct Gemini client for REST endpoints (bypasses Inngest)
from google import genai as _google_genai
from qdrant_client import QdrantClient as _QdrantClient
_gemini_client = _google_genai.Client()

inngest_client = inngest.Inngest(
    app_id="rag_proj",
    logger=logging.getLogger("rag_proj"),
    is_production=os.getenv("ENVIRONMENT") == "production",
    serializer=inngest.PydanticSerializer()
)


@inngest_client.create_function(
    fn_id="RAG: Ingest PDF",
    trigger=inngest.TriggerEvent(event="rag/ingest_pdf"),
)
async def rag_ingest_pdf(ctx: inngest.Context):
    def _load(ctx: inngest.Context) -> RAGChunkAndSrc:
        pdf_path = ctx.event.data["pdf_path"]
        subject = ctx.event.data.get("subject", "default")
        source_id = ctx.event.data.get("source_id", pdf_path)
        chunks = load_and_chunk_pdf(pdf_path)
        return RAGChunkAndSrc(chunks=chunks, source_id=source_id, subject=subject)

    def _upsert(chunks_and_src: RAGChunkAndSrc) -> RAGUpsertResult:
        chunks = chunks_and_src.chunks
        source_id = chunks_and_src.source_id
        subject = chunks_and_src.subject
        vecs = embed_texts(chunks)
        ids = [str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}:{i}")) for i in range(len(chunks))]
        payloads = [{"source": source_id, "text": chunks[i]} for i in range(len(chunks))]
        QdrantStorage(collection=subject).upsert(ids, vecs, payloads)
        return RAGUpsertResult(ingested=len(chunks), subject=subject)

    chunks_and_src = await ctx.step.run("load-and-chunk", lambda: _load(ctx), output_type=RAGChunkAndSrc)
    ingested = await ctx.step.run("embed-and-upsert", lambda: _upsert(chunks_and_src), output_type=RAGUpsertResult)
    return ingested.model_dump()


@inngest_client.create_function(
    fn_id="RAG: Query PDF",
    trigger=inngest.TriggerEvent(event="rag/query_pdf_ai")
)
async def rag_query_pdf_ai(ctx: inngest.Context):
    def _search(question: str, subject: str, top_k: int = 5) -> RAGSearchResult:
        query_vec = embed_texts([question])[0]
        store = QdrantStorage(collection=subject)
        found = store.search(query_vec, top_k)
        return RAGSearchResult(contexts=found["contexts"], sources=found["sources"], subject=subject)

    question = ctx.event.data["question"]
    subject = ctx.event.data.get("subject", "default")
    top_k = int(ctx.event.data.get("top_k", 5))

    found = await ctx.step.run("embed-and-search", lambda: _search(question, subject, top_k), output_type=RAGSearchResult)

    context_block = "\n\n".join(f"- {c}" for c in found.contexts)
    user_content = (
        f"Context from class materials:\n{context_block}\n\n"
        f"Student question: {question}"
    )

    adapter = ai.gemini.Adapter(
        auth_key=os.getenv("GEMINI_API_KEY"),
        model="gemini-3.6-flash"
    )

    res = await ctx.step.ai.infer(
        "llm-answer",
        adapter=adapter,
        body={
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": (
                        "You are a helpful study assistant. "
                        "When class material context is provided, prioritize answering from it and use the same notation and methods. "
                        "If the context is empty or does not contain relevant information, clearly state: "
                        "'I couldn't find anything relevant in the uploaded materials.' "
                        "Then answer the question using your general knowledge as a helpful AI assistant.\n\n"
                        + user_content
                    )}]
                }
            ],
            "generationConfig": {
                "maxOutputTokens": 1024,
                "temperature": 0.2
            }
        }
    )

    answer = res["candidates"][0]["content"]["parts"][0]["text"].strip()
    return {"answer": answer, "sources": found.sources, "num_contexts": len(found.contexts), "subject": subject}



app = FastAPI(title="StudyMate API")

# ── REST endpoints for Streamlit frontend ──────────────────────────────────────

class SubjectCreate(BaseModel):
    name: str

class QueryRequest(BaseModel):
    question: str
    top_k: int = 5

@app.get("/api/subjects")
def list_subjects():
    client = _QdrantClient(
        url=os.getenv("QDRANT_URL", "http://localhost:6333"),
        api_key=os.getenv("QDRANT_API_KEY")
    )
    cols = client.get_collections().collections
    return {"subjects": sorted([c.name for c in cols])}

@app.post("/api/subjects")
def create_subject(body: SubjectCreate):
    QdrantStorage(collection=body.name)   # creates collection if absent
    return {"subject": body.name, "created": True}

@app.post("/api/subjects/{subject}/upload")
def upload_pdf(subject: str, file: UploadFile = File(...)):
    import traceback
    suffix = Path(file.filename).suffix or ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    try:
        chunks = load_and_chunk_pdf(Path(tmp_path))   # Path() required by PDFReader
        vecs   = embed_texts(chunks)
        src    = file.filename
        ids    = [str(uuid.uuid5(uuid.NAMESPACE_URL, f"{src}:{i}")) for i in range(len(chunks))]
        payloads = [{"source": src, "text": chunks[i]} for i in range(len(chunks))]
        QdrantStorage(collection=subject).upsert(ids, vecs, payloads)
        return {"ingested": len(chunks), "subject": subject, "filename": file.filename}
    except Exception as e:
        logging.error(f"Upload failed: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(tmp_path)

@app.post("/api/subjects/{subject}/query")
def query_subject(subject: str, body: QueryRequest):
    query_vec = embed_texts([body.question])[0]
    found = QdrantStorage(collection=subject).search(query_vec, body.top_k)

    no_context = not found["contexts"]

    context_block = "\n\n".join(f"- {c}" for c in found["contexts"]) if not no_context else "(none)"
    prompt = (
        "You are a helpful study assistant. "
        "When class material context is provided, prioritize answering from it and use the same notation and methods. "
        "If the context is empty or marked as '(none)', clearly state at the start of your answer: "
        "'I couldn't find anything relevant in the uploaded materials.' "
        "Then answer the question using your general knowledge as a helpful AI assistant.\n\n"
        f"Context from class materials:\n{context_block}\n\n"
        f"Student question: {body.question}"
    )
    response = _gemini_client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    return {
        "answer": response.text,
        "sources": found["sources"],
        "num_contexts": len(found["contexts"]),
        "subject": subject
    }

# ── Inngest ────────────────────────────────────────────────────────────────────
inngest.fast_api.serve(app, inngest_client, [rag_ingest_pdf, rag_query_pdf_ai])