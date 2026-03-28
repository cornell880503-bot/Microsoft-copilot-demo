"""
Copilot Agent — orchestrates the full pipeline:
  1. Fetch active window context
  2. Semantic search over local docs
  3. Stream step-by-step thoughts via SSE
  4. Call Gemini Flash and emit structured result

SSE event shape:
  { "step": "context"|"search"|"think"|"result"|"error", "text"?: str, ...result fields }
"""

import json
import logging
import os
import re
from typing import AsyncGenerator

import google.generativeai as genai

from rag.searcher import search_docs
from window_context import get_active_window_title

logger = logging.getLogger(__name__)

# ── Model ─────────────────────────────────────────────────────────────────────
# Override with GEMINI_MODEL env var (e.g. "gemini-3-flash" when available)
DEFAULT_MODEL = "gemini-2.0-flash"

# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are Copilot, an intelligent desktop AI assistant embedded in the user's workflow.

You will receive:
- The user's currently active application window title
- The user's query
- Optionally: relevant excerpts from their local knowledge base

Your job is to analyze this context and choose the most useful action.

You MUST respond with ONLY a single valid JSON object — no markdown, no explanation, no code fences:
{
  "thought": "<1–2 sentence reasoning about what the user needs and why you chose this action>",
  "action": "<exactly one of: SEARCH_LOCAL_DOCS | DRAFT_CONTENT | GENERATE_IMAGE>",
  "payload": "<the actual useful output: answer, drafted text, image description, or refined search query>"
}

Action selection rules:
- SEARCH_LOCAL_DOCS  → user asks about local files, projects, or knowledge base content
- DRAFT_CONTENT      → user wants text written, summarized, explained, or analyzed
- GENERATE_IMAGE     → user explicitly asks to create, describe, or visualize an image

Tailor your tone to the active application context (e.g. be concise in a terminal, detailed in a doc editor).
"""


def _sse(data: dict) -> str:
    """Format a dict as a Server-Sent Event line."""
    return f"data: {json.dumps(data)}\n\n"


def _clean_json(raw: str) -> str:
    """Strip markdown code fences that Gemini sometimes wraps around JSON."""
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


def _build_prompt(user_input: str, active_window: str, rag_results: list[dict]) -> str:
    rag_section = ""
    if rag_results:
        excerpts = "\n---\n".join(
            f"[source: {r['source']}, score: {r['score']:.3f}]\n{r['content']}"
            for r in rag_results
        )
        rag_section = f"\n\nLocal Knowledge Base Results:\n{excerpts}"

    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"Active Application: {active_window or 'Unknown'}\n"
        f"User Query: {user_input}"
        f"{rag_section}"
    )


async def run_agent_stream(user_input: str) -> AsyncGenerator[str, None]:
    """
    Generator that yields SSE events driving the Copilot thought feed.
    Designed to be wrapped in a FastAPI StreamingResponse.
    """

    # ── Step 1: Window Context ─────────────────────────────────────────────
    yield _sse({"step": "context", "text": "Reading your active application..."})
    active_window = get_active_window_title() or "Unknown"
    yield _sse({"step": "context", "text": f"Active window: {active_window}"})

    # ── Step 2: Local RAG Search ───────────────────────────────────────────
    yield _sse({"step": "search", "text": "Searching local knowledge base..."})
    try:
        rag_results = search_docs(user_input, top_k=3)
        if rag_results:
            yield _sse({"step": "search", "text": f"Found {len(rag_results)} relevant document(s) (top score: {rag_results[0]['score']:.3f})"})
        else:
            yield _sse({"step": "search", "text": "No matching local documents found"})
    except Exception as e:
        logger.warning("RAG search failed: %s", e)
        rag_results = []
        yield _sse({"step": "search", "text": "Local search unavailable — proceeding without context"})

    # ── Step 3: Gemini ─────────────────────────────────────────────────────
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        yield _sse({"step": "error", "text": "GEMINI_API_KEY not set. Add it to server/.env"})
        return

    model_name = os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
    yield _sse({"step": "think", "text": f"Consulting {model_name}..."})

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        prompt = _build_prompt(user_input, active_window, rag_results)

        logger.info("Calling Gemini model=%s prompt_len=%d", model_name, len(prompt))
        response = model.generate_content(prompt)
        raw = _clean_json(response.text)

        result = json.loads(raw)

        # Validate required keys
        for key in ("thought", "action", "payload"):
            if key not in result:
                raise ValueError(f"Missing key '{key}' in Gemini response")

        yield _sse({"step": "think", "text": f"Decision: {result['action']}"})
        yield _sse({"step": "result", **result})

    except json.JSONDecodeError:
        logger.error("Gemini returned non-JSON: %s", response.text[:200])
        yield _sse({
            "step": "result",
            "thought": "Gemini returned a non-structured response; presenting as-is.",
            "action": "DRAFT_CONTENT",
            "payload": response.text,
        })
    except Exception as e:
        logger.exception("Agent error")
        yield _sse({"step": "error", "text": f"Agent error: {e}"})
