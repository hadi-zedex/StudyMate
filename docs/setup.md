# Local Setup Guide

## Prerequisites

- Python 3.11+
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for Qdrant)
- [Node.js](https://nodejs.org/) (for Inngest Dev Server)
- A [Google AI Studio](https://aistudio.google.com/) API key (free)

---

## 1. Clone & Create Virtual Environment

```powershell
git clone https://github.com/YOUR_USERNAME/studymate.git
cd studymate
python -m venv venv
.\venv\Scripts\Activate.ps1
```

## 2. Install Dependencies

```powershell
pip install -r requirements.txt
```

> **Note:** `sentence-transformers` will download the `BAAI/bge-small-en-v1.5` model (~46 MB) on first run automatically. No API key needed.

## 3. Configure Environment Variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_google_ai_studio_api_key_here
```

Get your free key at: https://aistudio.google.com/app/apikey

## 4. Start Qdrant (Vector Database)

Make sure Docker Desktop is running, then:

```powershell
docker run -d --name qdrantRagProj -p 6333:6333 qdrant/qdrant
```

To start it again after a system restart:

```powershell
docker start qdrantRagProj
```

Verify it's running at: http://localhost:6333/dashboard

## 5. Start the FastAPI Backend

```powershell
.\venv\Scripts\Activate.ps1
venv\Scripts\uvicorn.exe app.main:app --reload
```

The API will be available at: http://localhost:8000

## 6. Start the Inngest Dev Server

In a **separate terminal**:

```powershell
npx inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest --no-discovery
```

The Inngest dashboard will be available at: http://localhost:8288

## 7. Start the Streamlit Frontend

In a **separate terminal**:

```powershell
.\venv\Scripts\Activate.ps1
venv\Scripts\streamlit.exe run streamlit_app.py
```

The UI will be available at: http://localhost:8501

---

## Running Order (Every Session)

1. Open **Docker Desktop** and wait for it to start
2. Run `docker start qdrantRagProj`
3. Activate venv and run `venv\Scripts\uvicorn.exe app.main:app --reload`
4. In a new terminal, run the Inngest dev server command
5. In a new terminal, run `venv\Scripts\streamlit.exe run streamlit_app.py`
6. Open http://localhost:8501 to use the app
7. Open http://localhost:8288 to trigger Inngest events directly (optional)

---

## Using the App

1. Open http://localhost:8501
2. Click **➕ New Subject** in the sidebar (e.g. `physics-ii`)
3. Click **Upload PDF** and select your lecture notes or textbook
4. Type a question in the chat and press Enter

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `docker` not found | Restart PC after Docker Desktop install |
| `uvicorn` uses wrong Python | Use `venv\Scripts\uvicorn.exe` explicitly |
| Qdrant dimension mismatch | Delete collection: `docker restart qdrantRagProj` |
| Gemini 429 rate limit | Free tier limit reached — wait a few minutes |
| Inngest function not found | Make sure uvicorn is running **before** starting Inngest |
| Streamlit can't connect to API | Make sure uvicorn is running on port 8000 |
