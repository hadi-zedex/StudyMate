# 📚 StudyMate — AI Study Assistant

> Answer exam questions the way your professor taught them.

StudyMate is a RAG-powered study assistant that answers questions **based on your own class materials** — lecture slides, textbooks, and notes — not generic internet knowledge.

[![Live App](https://img.shields.io/badge/Live_Demo-Streamlit_App-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://studymate-ai-app.streamlit.app/)

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-latest-green)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-UI-red)](https://streamlit.io)
[![Qdrant](https://img.shields.io/badge/Qdrant-VectorDB-purple)](https://qdrant.tech)

🚀 **Live Website:** [studymate-ai-app.streamlit.app](https://studymate-ai-app.streamlit.app/)

---

## The Problem

When students use ChatGPT for exam prep, it answers using general knowledge. It doesn't know:
- The **specific method** your professor used
- The **notation** your textbook follows
- The **equations** derived in your lecture

## The Solution

Upload your class PDFs → ask questions → get answers using **your professor's exact approach**.

---

## Demo

```
Student: "Derive the work-energy theorem"

StudyMate: "Using the method from Lecture 3:
  Starting from Newton's second law F = ma,
  integrating both sides with respect to displacement...
  [answer follows the uploaded lecture notes]"
```

---

## Features

- 📂 **Multi-subject support** — separate knowledge bases per subject
- 📄 **PDF upload** — lecture slides, textbooks, scanned notes
- 🤖 **Grounded answers** — LLM strictly uses uploaded context
- 🔁 **Durable pipelines** — Inngest orchestrates ingestion with automatic retries
- 🌐 **Shareable** — deployed publicly, accessible to classmates

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Backend | FastAPI + Uvicorn |
| Job Orchestration | Inngest |
| PDF Chunking | LlamaIndex |
| Embeddings | `BAAI/bge-small-en-v1.5` (local, free) |
| Vector Database | Qdrant |
| LLM | Google Gemini `gemini-3.6-flash` (free tier) |

---

## Project Structure

```
studymate/
├── app/
│   ├── main.py           # FastAPI app + Inngest functions + REST API
│   ├── data_loader.py    # PDF loading, chunking, embedding
│   ├── vector_db.py      # Qdrant client wrapper
│   └── custom_types.py   # Pydantic models
├── streamlit_app.py      # Streamlit frontend
├── docs/
│   ├── overview.md       # Project overview
│   ├── setup.md          # Local setup guide
│   └── deployment.md     # Deployment guide
├── .streamlit/
│   └── config.toml       # Dark theme config
├── requirements.txt          # Backend dependencies
└── requirements-streamlit.txt # Frontend dependencies
```

---

## Local Setup

See [docs/setup.md](docs/setup.md) for full instructions.

**Quick start:**
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Add your Google API key to .env
echo "GEMINI_API_KEY=your_key_here" > .env

# 3. Start Qdrant
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant

# 4. Start FastAPI
uvicorn app.main:app --reload

# 5. Start Streamlit (new terminal)
streamlit run streamlit_app.py
```

---

## Deployment

See [docs/deployment.md](docs/deployment.md) for the full guide.

**Free deployment stack:**
- **FastAPI** → [Render](https://render.com) (free tier)
- **Streamlit** → [Streamlit Cloud](https://share.streamlit.io) (free)
- **Vector DB** → [Qdrant Cloud](https://cloud.qdrant.io) (free tier)

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | ✅ | Google AI Studio API key |
| `QDRANT_URL` | Production | Qdrant Cloud cluster URL |
| `QDRANT_API_KEY` | Production | Qdrant Cloud API key |
| `STUDYMATE_API_URL` | Streamlit Cloud | Render backend URL |
| `ENVIRONMENT` | Production | Set to `production` on Render |

---

## How It Works

```
INGESTION
PDF → Chunks (LlamaIndex) → Embeddings (bge-small) → Qdrant collection

QUERY
Question → Embed → Qdrant search → Top-k chunks → Gemini → Answer
```

Each subject is stored as a **separate Qdrant collection**, so Physics and Maths never mix.
