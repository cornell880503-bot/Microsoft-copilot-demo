"""
Copilot Agent — orchestrates the full pipeline:
  1. Fetch active window context
  2. Semantic search over local docs
  3. Stream step-by-step thoughts via SSE
  4. Call Gemini Flash and emit structured result
  5. If GENERATE_IMAGE: auto-augment prompt + call Gemini image model → base64

SSE event shape:
  { "step": "context"|"search"|"think"|"result"|"image"|"action_card"|"error", ... }
"""

import base64
import json
import logging
import os
import re
from pathlib import Path
from typing import AsyncGenerator

from google import genai
from google.genai import types

from rag.searcher import search_docs
from window_context import get_active_window_title

logger = logging.getLogger(__name__)

DEFAULT_MODEL       = "gemini-2.0-flash"
IMAGE_MODEL         = "gemini-3.1-flash-image-preview"
IMAGE_MODEL_FALLBACK = "gemini-2.0-flash-exp-image-generation"

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
  "action": "<exactly one of: SEARCH_LOCAL_DOCS | DRAFT_CONTENT | GENERATE_IMAGE | SEND_EMAIL | SAVE_FILE>",
  "payload": "<the actual useful output: answer, drafted text, image description, email body, or file content>"
}

Action selection rules:
- SEARCH_LOCAL_DOCS → user asks about local files, projects, or knowledge base content
- DRAFT_CONTENT     → user wants text written, summarized, explained, or analyzed
- GENERATE_IMAGE    → user explicitly asks to create, describe, or visualize an image
- SEND_EMAIL        → user wants to compose and send an email to someone
- SAVE_FILE         → user wants to save content to a file on their computer

For SEND_EMAIL, structure payload as JSON string:
{"to":"...","subject":"...","body":"...","attachment_path":"<absolute path to file if user mentioned attaching one, else null>"}
For SAVE_FILE, structure payload as JSON string: {"filename":"...","content":"..."}

Tailor your tone to the active application context.
"""

IMAGE_AUGMENT_PROMPT = """\
The user is currently working in: {active_window}
Original image request: {original_prompt}

Create an enhanced, detailed image generation prompt that:
1. Incorporates the context of the active application
2. Adds artistic style, lighting, and composition details
3. Is optimized for AI image generation

Respond with ONLY the enhanced prompt text, no explanation.
"""


def _find_cv_file() -> str | None:
    """
    Find the most recent CV/resume PDF by scanning known local directories.
    Prefers files with 'cv' or 'resume' in the name, sorted by modification time.
    """
    cv_keywords = {"cv", "resume", "curriculum"}
    search_dirs = [Path.home() / "Downloads", Path.home() / "Documents", Path.home() / "Desktop"]
    extra = os.getenv("EXTRA_DATA_DIRS", "")
    for p in extra.split(":"):
        if p.strip():
            search_dirs.append(Path(p.strip()).expanduser())

    candidates = []
    for folder in search_dirs:
        if not folder.exists():
            continue
        for f in folder.glob("*.pdf"):
            if any(kw in f.name.lower() for kw in cv_keywords):
                candidates.append(f)

    if not candidates:
        return None

    # Return the most recently modified CV file
    candidates.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    logger.info("Found CV candidates: %s", [f.name for f in candidates[:3]])
    return str(candidates[0])


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


def _clean_json(raw: str) -> str:
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


async def _generate_image(
    client: genai.Client,
    original_prompt: str,
    active_window: str,
    model_name: str,
) -> tuple[str | None, str]:
    """
    Auto-augment the prompt with window context, then generate image.
    Returns (base64_png_or_none, augmented_prompt).
    """
    # Step 1: augment the prompt
    aug_response = client.models.generate_content(
        model=model_name,
        contents=IMAGE_AUGMENT_PROMPT.format(
            active_window=active_window,
            original_prompt=original_prompt,
        ),
    )
    augmented = aug_response.text.strip()
    logger.info("Augmented image prompt: %s", augmented[:120])

    # Step 2: generate image with Gemini image model
    image_model = os.getenv("GEMINI_IMAGE_MODEL", IMAGE_MODEL)
    try:
        img_response = client.models.generate_content(
            model=image_model,
            contents=augmented,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )
        for part in img_response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                b64 = base64.b64encode(part.inline_data.data).decode("utf-8")
                mime = part.inline_data.mime_type
                return f"data:{mime};base64,{b64}", augmented
    except Exception as e:
        logger.error("Image generation failed with %s: %s", image_model, e)
        # Try fallback model
        try:
            img_response = client.models.generate_content(
                model=IMAGE_MODEL_FALLBACK,
                contents=augmented,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                ),
            )
            for part in img_response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    b64 = base64.b64encode(part.inline_data.data).decode("utf-8")
                    mime = part.inline_data.mime_type
                    return f"data:{mime};base64,{b64}", augmented
        except Exception as e2:
            logger.error("Fallback image model also failed: %s", e2)

    return None, augmented


async def run_agent_stream(user_input: str) -> AsyncGenerator[str, None]:
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

    # ── Step 3: Gemini Decision ────────────────────────────────────────────
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        yield _sse({"step": "error", "text": "GEMINI_API_KEY not set. Add it to server/.env"})
        return

    model_name = os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
    yield _sse({"step": "think", "text": f"Consulting {model_name}..."})

    try:
        client = genai.Client(api_key=api_key)
        prompt = _build_prompt(user_input, active_window, rag_results)

        response = client.models.generate_content(model=model_name, contents=prompt)
        raw = _clean_json(response.text)
        result = json.loads(raw)

        for key in ("thought", "action", "payload"):
            if key not in result:
                raise ValueError(f"Missing key '{key}' in Gemini response")

        action = result["action"]
        yield _sse({"step": "think", "text": f"Decision: {action}"})

        # ── Image Generation ───────────────────────────────────────────────
        if action == "GENERATE_IMAGE":
            yield _sse({"step": "think", "text": "Auto-augmenting image prompt with window context..."})
            image_data, augmented_prompt = await _generate_image(
                client, result["payload"], active_window, model_name
            )
            yield _sse({"step": "think", "text": f"Prompt: {augmented_prompt[:80]}..."})
            if image_data:
                yield _sse({
                    "step": "image",
                    "thought": result["thought"],
                    "action": action,
                    "image_data": image_data,
                    "prompt": augmented_prompt,
                })
            else:
                yield _sse({
                    "step": "result",
                    "thought": result["thought"],
                    "action": "DRAFT_CONTENT",
                    "payload": f"Image generation unavailable. Enhanced prompt:\n\n{augmented_prompt}",
                })
            return

        # ── Action Cards (SEND_EMAIL / SAVE_FILE) ──────────────────────────
        if action in ("SEND_EMAIL", "SAVE_FILE"):
            try:
                action_payload = json.loads(result["payload"]) if isinstance(result["payload"], str) else result["payload"]
            except (json.JSONDecodeError, TypeError):
                action_payload = {"content": result["payload"]}

            # Auto-attach: if SEND_EMAIL has no attachment_path but the user
            # mentioned CV/resume, find the best PDF from RAG results
            if action == "SEND_EMAIL" and not action_payload.get("attachment_path"):
                cv_keywords = {"cv", "resume", "curriculum vitae"}
                if any(kw in user_input.lower() for kw in cv_keywords):
                    pdf_path = _find_cv_file()
                    if pdf_path:
                        action_payload["attachment_path"] = pdf_path
                        yield _sse({"step": "search", "text": f"Auto-attaching CV: {Path(pdf_path).name}"})

            yield _sse({
                "step": "action_card",
                "thought": result["thought"],
                "action": action,
                "payload": action_payload,
            })
            return

        # ── Default result ─────────────────────────────────────────────────
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
