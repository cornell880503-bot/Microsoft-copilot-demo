"""
Semantic search over the local ChromaDB vector store.
"""

import logging
from typing import List

from langchain_chroma import Chroma
from .indexer import get_vector_store

logger = logging.getLogger(__name__)


def search_docs(query: str, top_k: int = 5) -> List[dict]:
    """
    Perform a semantic similarity search against the local vector store.

    Returns a list of result dicts:
        { "content": str, "source": str, "score": float }

    Score is the cosine similarity (higher = more relevant, range 0–1).
    """
    store: Chroma = get_vector_store()

    # similarity_search_with_relevance_scores returns (Document, score) pairs
    results = store.similarity_search_with_relevance_scores(query, k=top_k)

    if not results:
        logger.info("No results for query: %r", query)
        return []

    output = []
    for doc, score in results:
        output.append({
            "content": doc.page_content,
            "source":  doc.metadata.get("source", "unknown"),
            "score":   round(float(score), 4),
        })

    logger.info("Query %r → %d results (top score: %.4f)", query, len(output), output[0]["score"])
    return output
