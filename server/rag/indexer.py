"""
Indexes all .txt files in ./local_data into a persistent ChromaDB vector store.
Uses HuggingFace sentence-transformers (all-MiniLM-L6-v2) — fully local, no API key.
"""

import os
import logging
from pathlib import Path

from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

logger = logging.getLogger(__name__)

# Paths (resolved relative to this file so they work as a sidecar)
_SERVER_DIR  = Path(__file__).parent.parent
LOCAL_DATA   = _SERVER_DIR / "local_data"
CHROMA_DIR   = _SERVER_DIR / "chroma_store"
COLLECTION   = "local_docs"
EMBED_MODEL  = "all-MiniLM-L6-v2"


def _get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=EMBED_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def get_vector_store() -> Chroma:
    """Return the persistent Chroma vector store (creates it if missing)."""
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=COLLECTION,
        embedding_function=_get_embeddings(),
        persist_directory=str(CHROMA_DIR),
    )


def index_local_data() -> dict:
    """
    Scan ./local_data for .txt files, chunk them, and upsert into ChromaDB.
    Returns a summary dict with file count and chunk count.
    """
    LOCAL_DATA.mkdir(parents=True, exist_ok=True)

    txt_files = list(LOCAL_DATA.glob("*.txt"))
    if not txt_files:
        logger.warning("No .txt files found in %s", LOCAL_DATA)
        return {"files_indexed": 0, "chunks_added": 0, "message": "No .txt files found in local_data/"}

    # Load all .txt files
    loader = DirectoryLoader(
        str(LOCAL_DATA),
        glob="*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        show_progress=False,
    )
    docs = loader.load()
    logger.info("Loaded %d documents from %s", len(docs), LOCAL_DATA)

    # Split into chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    logger.info("Split into %d chunks", len(chunks))

    # Upsert into ChromaDB
    store = get_vector_store()
    store.add_documents(chunks)
    logger.info("Indexed %d chunks into ChromaDB collection '%s'", len(chunks), COLLECTION)

    return {
        "files_indexed": len(txt_files),
        "chunks_added": len(chunks),
        "files": [f.name for f in txt_files],
    }
