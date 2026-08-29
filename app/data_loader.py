# from google import genai
from sentence_transformers import SentenceTransformer
from llama_index.readers.file import PDFReader
from llama_index.core.node_parser import SentenceSplitter
from dotenv import load_dotenv

load_dotenv()

_embed_model = SentenceTransformer("BAAI/bge-small-en-v1.5")
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
EMBED_DIM = 384

splitter = SentenceSplitter(chunk_size=1000, chunk_overlap=200)

def load_and_chunk_pdf(path: str):
    docs = PDFReader().load_data(file=path)
    texts = [d.text for d in docs if getattr(d, "text", None)]
    chunks = []
    for t in texts:
        chunks.extend(splitter.split_text(t))
    return chunks


def embed_texts(texts: list[str]) -> list[list[float]]:
    return _embed_model.encode(texts, normalize_embeddings=True).tolist()



# client = genai.Client()
# EMBED_MODEL = "models/gemini-embedding-001"
# EMBED_DIM = 768
# def embed_texts_genai(texts: list[str], batch_size: int = 20) -> list[list[float]]:
#     import time
#     all_embeddings = []
#     for i in range(0, len(texts), batch_size):
#         batch = texts[i:i + batch_size]
#         for attempt in range(4):
#             try:
#                 response = client.models.embed_content(model=EMBED_MODEL, contents=batch)
#                 all_embeddings.extend([e.values for e in response.embeddings])
#                 break
#             except Exception as e:
#                 if "429" in str(e) and attempt < 3:
#                     wait = 10 * (2 ** attempt)
#                     print(f"Rate limited. Waiting {wait}s before retry...")
#                     time.sleep(wait)
#                 else:
#                     raise
#         if i + batch_size < len(texts):
#             time.sleep(1)
#     return all_embeddings
# ---------------------------------------------------------