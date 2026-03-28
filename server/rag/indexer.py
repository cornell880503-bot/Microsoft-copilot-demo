"""
Indexes .txt and .md files from one or more folders into a persistent ChromaDB vector store.
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

_SERVER_DIR = Path(__file__).parent.parent
LOCAL_DATA  = _SERVER_DIR / "local_data"
CHROMA_DIR  = _SERVER_DIR / "chroma_store"
COLLECTION  = "local_docs"
EMBED_MODEL = "all-MiniLM-L6-v2"

# Extra folders to index, read from env var EXTRA_DATA_DIRS (colon-separated paths)
# e.g. EXTRA_DATA_DIRS=/Users/you/Downloads:/Users/you/Documents
def _extra_dirs() -> list[Path]:
    raw = os.getenv("EXTRA_DATA_DIRS", "")
    return [Path(p).expanduser() for p in raw.split(":") if p.strip()]


def _get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=EMBED_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def get_vector_store() -> Chroma:
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=COLLECTION,
        embedding_function=_get_embeddings(),
        persist_directory=str(CHROMA_DIR),
    )


def index_local_data(extra_dirs: list[str] | None = None) -> dict:
    """
    Scan local_data/ plus any extra_dirs for .txt and .md files,
    chunk them, and upsert into ChromaDB.

    extra_dirs: list of absolute path strings (from API call or env var).
    """
    LOCAL_DATA.mkdir(parents=True, exist_ok=True)

    # Collect all directories to scan
    scan_dirs: list[Path] = [LOCAL_DATA] + _extra_dirs()
    if extra_dirs:
        scan_dirs += [Path(p).expanduser() for p in extra_dirs if p.strip()]

    all_files: list[Path] = []
    all_docs  = []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    for scan_dir in scan_dirs:
        if not scan_dir.exists():
            logger.warning("Directory not found, skipping: %s", scan_dir)
            continue

        for glob in ("*.txt", "*.md"):
            files = list(scan_dir.glob(glob))
            all_files.extend(files)

            for f in files:
                try:
                    loader = TextLoader(str(f), encoding="utf-8")
                    docs = loader.load()
                    chunks = splitter.split_documents(docs)
                    all_docs.extend(chunks)
                    logger.info("Indexed %s → %d chunks", f.name, len(chunks))
                except Exception as e:
                    logger.warning("Skipping %s: %s", f.name, e)

    if not all_files:
        return {"files_indexed": 0, "chunks_added": 0, "message": "No .txt or .md files found in scanned directories"}

    store = get_vector_store()
    store.add_documents(all_docs)

    return {
        "files_indexed": len(all_files),
        "chunks_added": len(all_docs),
        "files": [str(f) for f in all_files],
        "dirs_scanned": [str(d) for d in scan_dirs],
    }
