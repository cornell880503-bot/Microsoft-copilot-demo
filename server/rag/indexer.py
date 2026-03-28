"""
Indexes .txt, .md, .pdf, and image (.png/.jpg) files from one or more folders
into a persistent ChromaDB vector store.
"""

import logging
import os
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema import Document

logger = logging.getLogger(__name__)

_SERVER_DIR = Path(__file__).parent.parent
LOCAL_DATA  = _SERVER_DIR / "local_data"
CHROMA_DIR  = _SERVER_DIR / "chroma_store"
COLLECTION  = "local_docs"
EMBED_MODEL = "all-MiniLM-L6-v2"

SUPPORTED_EXTS = {".txt", ".md", ".pdf", ".png", ".jpg", ".jpeg"}


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


def _load_pdf(path: Path) -> list[Document]:
    loader = PyPDFLoader(str(path))
    return loader.load()


def _load_image(path: Path) -> list[Document]:
    try:
        import pytesseract
        from PIL import Image
        text = pytesseract.image_to_string(Image.open(path))
        if not text.strip():
            logger.warning("OCR returned empty text for %s", path.name)
            return []
        return [Document(page_content=text, metadata={"source": str(path)})]
    except ImportError:
        logger.error(
            "pytesseract or Pillow not installed. Run: pip install pytesseract Pillow"
        )
        return []
    except Exception as e:
        logger.warning("OCR failed for %s: %s", path.name, e)
        return []


def _load_text(path: Path) -> list[Document]:
    loader = TextLoader(str(path), encoding="utf-8")
    return loader.load()


def _load_file(path: Path) -> list[Document]:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return _load_pdf(path)
    elif ext in {".png", ".jpg", ".jpeg"}:
        return _load_image(path)
    else:
        return _load_text(path)


def index_local_data(extra_dirs: list[str] | None = None) -> dict:
    """
    Scan local_data/ plus any extra_dirs for supported files,
    chunk them, and upsert into ChromaDB.
    Supported: .txt  .md  .pdf  .png  .jpg  .jpeg
    """
    LOCAL_DATA.mkdir(parents=True, exist_ok=True)

    scan_dirs: list[Path] = [LOCAL_DATA] + _extra_dirs()
    if extra_dirs:
        scan_dirs += [Path(p).expanduser() for p in extra_dirs if p.strip()]

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    all_files: list[Path] = []
    all_chunks: list[Document] = []
    skipped: list[str] = []

    for scan_dir in scan_dirs:
        if not scan_dir.exists():
            logger.warning("Directory not found, skipping: %s", scan_dir)
            continue

        files = [f for f in scan_dir.iterdir()
                 if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS]

        for f in files:
            all_files.append(f)
            try:
                docs = _load_file(f)
                if docs:
                    chunks = splitter.split_documents(docs)
                    all_chunks.extend(chunks)
                    logger.info("%-40s → %d chunks", f.name, len(chunks))
                else:
                    skipped.append(f.name)
            except Exception as e:
                logger.warning("Skipping %s: %s", f.name, e)
                skipped.append(f.name)

    if not all_files:
        return {
            "files_indexed": 0,
            "chunks_added": 0,
            "message": f"No supported files found ({', '.join(SUPPORTED_EXTS)})",
        }

    store = get_vector_store()
    store.add_documents(all_chunks)

    return {
        "files_indexed": len(all_files) - len(skipped),
        "chunks_added": len(all_chunks),
        "files": [str(f) for f in all_files if f.name not in skipped],
        "skipped": skipped,
        "dirs_scanned": [str(d) for d in scan_dirs],
    }
