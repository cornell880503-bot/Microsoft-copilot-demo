"""
Project Copilot — Python FastAPI Sidecar
=========================================
Runs alongside the Electron app on http://localhost:8765

Endpoints:
  GET  /health            — liveness probe
  GET  /get-active-window — foreground app title
  POST /index-docs        — index local_data/*.txt into ChromaDB
  POST /search-docs       — semantic similarity search
  POST /agent/run         — full agent pipeline (SSE streaming)
"""

import logging
import os
from contextlib import asynccontextmanager

from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agent import run_agent_stream
from email_sender import send_email
from window_context import get_active_window_title
from rag.indexer import index_local_data
from rag.searcher import search_docs

load_dotenv(Path(__file__).parent / ".env")

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("copilot.server")


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Copilot sidecar starting on http://localhost:8765")
    yield
    logger.info("Copilot sidecar shutting down")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Project Copilot Sidecar",
    version="1.0.0",
    description="System context & RAG layer for the Copilot Electron shell",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "app://.", "file://"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ───────────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(5, ge=1, le=20)

class SearchResult(BaseModel):
    content: str
    source: str
    score: float

class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    total: int

class IndexRequest(BaseModel):
    extra_dirs: list[str] = Field(default_factory=list, description="Extra absolute folder paths to index")

class HistoryMessage(BaseModel):
    role: str       # "user" | "assistant"
    content: str

class AgentRequest(BaseModel):
    query:   str = Field(..., min_length=1, max_length=2000)
    history: list[HistoryMessage] = Field(default_factory=list)

class SaveFileRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    content:  str = Field(...)

class SendEmailRequest(BaseModel):
    to:              str = Field(..., min_length=1)
    subject:         str = Field(...)
    body:            str = Field(...)
    attachment_path: str | None = Field(None)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "copilot-sidecar"}


@app.get("/get-active-window")
async def get_active_window():
    title = get_active_window_title()
    if title is None:
        raise HTTPException(status_code=503, detail="Could not determine active window")
    return {"active_window": title}


@app.post("/index-docs")
async def index_docs(body: IndexRequest = IndexRequest()):
    try:
        result = index_local_data(extra_dirs=body.extra_dirs or None)
        logger.info("Indexing complete: %s", result)
        return result
    except Exception as e:
        logger.exception("Indexing failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search-docs", response_model=SearchResponse)
async def search_documents(body: SearchRequest):
    try:
        results = search_docs(body.query, top_k=body.top_k)
        return SearchResponse(
            query=body.query,
            results=[SearchResult(**r) for r in results],
            total=len(results),
        )
    except Exception as e:
        logger.exception("Search failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/send-email")
async def send_email_endpoint(body: SendEmailRequest):
    """Send a real email via Gmail/Outlook SMTP with optional file attachment."""
    logger.info("send-email called: to=%r subject=%r attachment_path=%r", body.to, body.subject, body.attachment_path)
    try:
        result = send_email(
            to=body.to,
            subject=body.subject,
            body=body.body,
            attachment_path=body.attachment_path,
        )
        logger.info("Email sent: %s", result)
        return result
    except Exception as e:
        logger.exception("Failed to send email")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/save-file")
async def save_file(body: SaveFileRequest):
    """Write content to ~/Downloads/<filename>. Returns the saved path."""
    # Sanitize filename — strip path separators to prevent directory traversal
    safe_name = Path(body.filename).name
    if not safe_name:
        raise HTTPException(status_code=400, detail="Invalid filename")

    save_path = Path.home() / "Downloads" / safe_name
    try:
        save_path.write_text(body.content, encoding="utf-8")
        logger.info("Saved file: %s", save_path)
        return {"saved_to": str(save_path), "filename": safe_name}
    except Exception as e:
        logger.exception("Failed to save file")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent/run")
async def agent_run(body: AgentRequest):
    """
    Full Copilot agent pipeline streamed as Server-Sent Events.

    Each event: data: {"step": "context"|"search"|"think"|"result"|"error", ...}\n\n

    The final 'result' event contains:
      {"step": "result", "thought": str, "action": str, "payload": str}
    """
    return StreamingResponse(
        run_agent_stream(body.query, [{"role": m.role, "content": m.content} for m in body.history]),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
