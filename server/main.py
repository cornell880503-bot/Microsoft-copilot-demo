"""
Project Copilot — Python FastAPI Sidecar
=========================================
Runs alongside the Electron app on http://localhost:8765

Endpoints:
  GET  /health          — liveness probe
  GET  /get-active-window — returns the user's current foreground app title
  POST /index-docs      — scans ./local_data/*.txt and indexes into ChromaDB
  POST /search-docs     — semantic search over the vector store
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from window_context import get_active_window_title
from rag.indexer import index_local_data
from rag.searcher import search_docs

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("copilot.server")


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────

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

# Allow requests from the Electron renderer (localhost:5173 in dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "app://.", "file://"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ───────────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    top_k: int = Field(5, ge=1, le=20, description="Number of results to return")


class SearchResult(BaseModel):
    content: str
    source: str
    score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    total: int


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "copilot-sidecar"}


@app.get("/get-active-window")
async def get_active_window():
    """
    Returns the title of the user's currently active/foreground application.
    Cross-platform: Win32 / AppleScript (macOS) / xdotool (Linux).
    """
    title = get_active_window_title()
    if title is None:
        raise HTTPException(status_code=503, detail="Could not determine active window")
    return {"active_window": title}


@app.post("/index-docs")
async def index_docs():
    """
    Scans ./local_data/*.txt, chunks the content, and upserts into ChromaDB.
    Safe to call multiple times — duplicate chunks are deduplicated by ChromaDB.
    """
    try:
        result = index_local_data()
        logger.info("Indexing complete: %s", result)
        return result
    except Exception as e:
        logger.exception("Indexing failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search-docs", response_model=SearchResponse)
async def search_documents(body: SearchRequest):
    """
    Semantic similarity search over the indexed local documents.
    Returns the top-k most relevant chunks with their source file and score.
    """
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
