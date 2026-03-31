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
import sys
import tempfile
from pathlib import Path
from typing import AsyncGenerator

from google import genai
from google.genai import types

from rag.searcher import search_docs
from window_context import get_active_window_title, capture_screen_base64, get_active_document_content

logger = logging.getLogger(__name__)

DEFAULT_MODEL       = "gemini-2.0-flash"
IMAGE_MODEL         = "gemini-3.1-flash-image-preview"
IMAGE_MODEL_FALLBACK = "gemini-2.0-flash-exp-image-generation"

# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are Copilot, an intelligent desktop AI assistant embedded in the user's workflow.

You will receive:
- The user's currently active application window title
- A screenshot of the user's screen (when available) — you CAN see what is on their screen
- The user's query
- Optionally: relevant excerpts from their local knowledge base

Your job is to analyze this context and choose the most useful action.

You MUST respond with ONLY a single valid JSON object — no markdown, no explanation, no code fences:
{
  "thought": "<1–2 sentence reasoning about what the user needs and why you chose this action>",
  "action": "<exactly one of: SEARCH_LOCAL_DOCS | DRAFT_CONTENT | GENERATE_IMAGE | SEND_EMAIL | SAVE_FILE | SCHEDULE_MEETING | OPEN_APP | EXECUTE_PYTHON>",
  "payload": "<the actual useful output: answer, drafted text, image description, email body, file content, or structured JSON>"
}

Action selection rules:
- SEARCH_LOCAL_DOCS  → user wants to find, locate, or browse files/documents on their computer — always use this when user asks to "find", "search for", "look for", or "show me" a file
- DRAFT_CONTENT      → user wants text written, summarized, explained, or analyzed
- GENERATE_IMAGE     → user explicitly asks to create, describe, or visualize an image
- SEND_EMAIL         → user wants to compose and send an email to someone
- SAVE_FILE          → user wants to save content to a file on their computer
- SCHEDULE_MEETING   → user wants to create a calendar event or schedule a meeting
- OPEN_APP           → user explicitly asks to LAUNCH a specific application by name (e.g. "open Spotify", "open Chrome"); NOT for finding files
- EXECUTE_PYTHON     → user wants to analyze, count, calculate, or process data from the active document using Python — write and run actual code (use when user says "用python", "analyze", "calculate", "count", "分析", "計算")

IMPORTANT: Never use OPEN_APP to open a file — use SEARCH_LOCAL_DOCS to find it first, then the user will choose to open it themselves.
IMPORTANT: When user asks to analyze/calculate data from a file (e.g. count ratios, statistics), always use EXECUTE_PYTHON — NOT DRAFT_CONTENT.

For EXECUTE_PYTHON, set payload to exactly the string "GENERATE_CODE" — the system will handle code generation separately.

For SEND_EMAIL, structure payload as JSON string:
{"to":"...","subject":"...","body":"...","attachment_path":null}
CRITICAL rules for the body field:
- Write as the sender (user), addressed TO the recipient — a complete professional email ready to send
- NEVER mention file paths, system paths, or technical details in the body
- NEVER ask for clarification or write meta-commentary — just write the email
- attachment_path must always be null (the system handles attachments automatically)

For SAVE_FILE, structure payload as JSON string:
{"filename":"...","content":"..."}

For SCHEDULE_MEETING, structure payload as JSON string:
{"title":"...","attendees":"...","date":"YYYY-MM-DD","time":"HH:MM","duration_minutes":60,"location":"..."}
- date must be a real future date in YYYY-MM-DD format
- time must be 24-hour HH:MM format
- attendees is a comma-separated list of names or email addresses

For OPEN_APP, structure payload as JSON string:
{"app":"...","action":"..."}
- app is the exact macOS application name (e.g. "Google Chrome", "Spotify", "Numbers")
- action is what to do after opening (e.g. "search for Microsoft Copilot news", or "" if just opening)

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


_LAST_IMAGE_PATH = Path(tempfile.gettempdir()) / "copilot_last_image.png"


def _find_cv_file() -> str | None:
    """
    Find the most recent CV/resume PDF by scanning known local directories.
    First tries files with cv/resume keywords in the name; falls back to
    the most recently modified PDF in Downloads.
    """
    cv_keywords = {"cv", "resume", "curriculum", "簡歷", "履歷", "profile"}
    search_dirs = [Path.home() / "Downloads", Path.home() / "Documents", Path.home() / "Desktop"]
    extra = os.getenv("EXTRA_DATA_DIRS", "")
    for p in extra.split(":"):
        if p.strip():
            search_dirs.append(Path(p.strip()).expanduser())

    # Pass 1: keyword match
    candidates = []
    all_pdfs = []
    for folder in search_dirs:
        if not folder.exists():
            continue
        for f in folder.glob("*.pdf"):
            all_pdfs.append(f)
            if any(kw in f.name.lower() for kw in cv_keywords):
                candidates.append(f)

    if candidates:
        candidates.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        logger.info("Found CV by keyword: %s", [f.name for f in candidates[:3]])
        return str(candidates[0])

    # Pass 2: fallback — most recently modified PDF anywhere in search dirs
    if all_pdfs:
        all_pdfs.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        logger.info("No keyword match — falling back to most recent PDF: %s", all_pdfs[0].name)
        return str(all_pdfs[0])

    return None


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


def _clean_json(raw: str) -> str:
    raw = raw.strip()
    # Strip markdown code fences
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    raw = raw.strip()
    # If still not a bare JSON object, extract the first {...} block
    if not raw.startswith("{"):
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            raw = m.group(0)
    return raw


async def generate_suggestions(active_window: str) -> list[str]:
    """Generate 2-3 proactive action suggestions based on the active window."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or not active_window or active_window in ("Unknown", ""):
        return []
    try:
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", DEFAULT_MODEL),
            contents=(
                f"The user is currently working in: {active_window}\n\n"
                "Generate exactly 3 short, specific action suggestions for a Copilot AI assistant "
                "based on what the user is likely doing in this app. "
                "Each suggestion must be 4-8 words, start with a verb, and be directly useful. "
                "Reply with ONLY a valid JSON array of 3 strings, no explanation:\n"
                '["suggestion 1", "suggestion 2", "suggestion 3"]'
            ),
        )
        raw = re.sub(r"^```(?:json)?\s*", "", resp.text.strip())
        raw = re.sub(r"\s*```$", "", raw).strip()
        result = json.loads(raw)[:3]
        logger.info("Suggestions for '%s': %s", active_window, result)
        return result
    except Exception as e:
        logger.warning("generate_suggestions failed for '%s': %s", active_window, e)
        return []


async def generate_chat_title(user_query: str) -> str:
    """Ask Gemini for a 4-6 word chat title based on the first user message."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model   = os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
    if not api_key:
        return user_query[:48]
    try:
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model=model,
            contents=(
                f"Give a 4-6 word chat title for a conversation that starts with this message. "
                f"Reply with ONLY the title, no punctuation, no quotes:\n\n{user_query[:300]}"
            ),
        )
        return resp.text.strip()[:60] or user_query[:48]
    except Exception:
        return user_query[:48]


def _build_user_turn(user_input: str, active_window: str, rag_results: list[dict],
                     doc_text: str | None = None, doc_path: str | None = None) -> str:
    """Build the current user turn text (system prompt goes in system_instruction)."""
    rag_section = ""
    if rag_results:
        excerpts = "\n---\n".join(
            f"[source: {r['source']}, score: {r['score']:.3f}]\n{r['content']}"
            for r in rag_results
        )
        rag_section = f"\n\nLocal Knowledge Base Results:\n{excerpts}"
    doc_section = ""
    if doc_path:
        fname = Path(doc_path).name if doc_path else "document"
        ext = Path(doc_path).suffix.lower() if doc_path else ""
        if doc_text and ext not in (".csv", ".xlsx", ".xls"):
            # For non-data files (PDF, Word, etc.) embed full text for reading/summarizing
            doc_section = f"\n\nActive Document — {fname} (path: {doc_path}):\n{doc_text}"
        elif doc_text:
            # For data files: provide only the first few rows so AI knows the schema,
            # but MUST use DOC_PATH env var to read the full file in code
            preview = "\n".join(doc_text.splitlines()[:8])
            doc_section = (
                f"\n\nActive Document — {fname}\n"
                f"Full file path (use this in code): {doc_path}\n"
                f"File preview (first 8 rows):\n{preview}\n"
                f"NOTE: Do NOT hardcode data. Always read the file using: "
                f"pd.read_csv(os.environ['DOC_PATH']) or equivalent."
            )
        else:
            doc_section = f"\n\nActive Document path: {doc_path}"
    return (
        f"Active Application: {active_window or 'Unknown'}\n"
        f"User Query: {user_input}"
        f"{doc_section}"
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
                raw_bytes = part.inline_data.data
                _LAST_IMAGE_PATH.write_bytes(raw_bytes)
                logger.info("Saved generated image to %s", _LAST_IMAGE_PATH)
                b64 = base64.b64encode(raw_bytes).decode("utf-8")
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
                    raw_bytes = part.inline_data.data
                    _LAST_IMAGE_PATH.write_bytes(raw_bytes)
                    logger.info("Saved generated image to %s", _LAST_IMAGE_PATH)
                    b64 = base64.b64encode(raw_bytes).decode("utf-8")
                    mime = part.inline_data.mime_type
                    return f"data:{mime};base64,{b64}", augmented
        except Exception as e2:
            logger.error("Fallback image model also failed: %s", e2)

    return None, augmented


async def run_agent_stream(user_input: str, history: list[dict] | None = None) -> AsyncGenerator[str, None]:
    # ── Step 1: Window Context ─────────────────────────────────────────────
    yield _sse({"step": "context", "text": "Reading your active application..."})
    active_window = get_active_window_title() or "Unknown"
    yield _sse({"step": "context", "text": f"Active window: {active_window}"})

    # Try document text extraction first (accurate); fall back to screenshot
    yield _sse({"step": "context", "text": "Reading active document content..."})
    doc_text, doc_path = get_active_document_content()
    screen_b64 = None
    if doc_text:
        fname = Path(doc_path).name if doc_path else "document"
        yield _sse({"step": "context", "text": f"Extracted text from {fname} ({len(doc_text)} chars) — not uploaded anywhere"})
    else:
        yield _sse({"step": "context", "text": "No document detected — capturing screen..."})
        screen_b64 = capture_screen_base64()
        if screen_b64:
            yield _sse({"step": "context", "text": "Screen captured — sent to AI, not stored locally"})
        else:
            yield _sse({"step": "context", "text": "Screen capture unavailable"})

    # ── Step 2: Local RAG Search ───────────────────────────────────────────
    yield _sse({"step": "search", "text": "Searching local knowledge base..."})
    try:
        rag_results = search_docs(user_input, top_k=3)
        if rag_results:
            yield _sse({"step": "search", "text": f"Found {len(rag_results)} relevant document(s) (top score: {rag_results[0]['score']:.3f})"})
        else:
            yield _sse({"step": "heal", "text": "No local documents matched — AI expanding to general knowledge..."})
            rag_results = []
    except Exception as e:
        logger.warning("RAG search failed: %s", e)
        rag_results = []
        yield _sse({"step": "heal", "text": "Local knowledge base unavailable — AI is falling back to general reasoning..."})

    # ── Step 3: Gemini Decision ────────────────────────────────────────────
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        yield _sse({"step": "error", "text": "GEMINI_API_KEY not set. Add it to server/.env"})
        return

    model_name = os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
    yield _sse({"step": "think", "text": f"Consulting {model_name}..."})

    try:
        client = genai.Client(api_key=api_key)

        # Build multi-turn contents: previous history + current user turn
        contents = []
        for msg in (history or []):
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        # Current turn: include screenshot if available
        user_text = _build_user_turn(user_input, active_window, rag_results, doc_text, doc_path)
        if screen_b64:
            current_parts = [
                {"inline_data": {"mime_type": "image/png", "data": screen_b64}},
                {"text": user_text},
            ]
        else:
            current_parts = [{"text": user_text}]
        contents.append({"role": "user", "parts": current_parts})

        logger.info("Sending %d-turn conversation to Gemini", len(contents))
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
        )
        raw = _clean_json(response.text)
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            # Self-healing: retry with an explicit re-prompt
            yield _sse({"step": "heal", "text": "Response format error — AI is self-correcting and retrying..."})
            logger.warning("Gemini returned non-JSON on first attempt, retrying: %s", response.text[:200])
            retry_contents = contents + [
                {"role": "model", "parts": [{"text": response.text}]},
                {"role": "user", "parts": [{"text": (
                    "Your previous response was not valid JSON. "
                    "You MUST reply with ONLY a single valid JSON object using exactly this schema, "
                    "no markdown, no explanation:\n"
                    '{"thought":"...","action":"...","payload":"..."}'
                )}]},
            ]
            response = client.models.generate_content(
                model=model_name,
                contents=retry_contents,
                config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
            )
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

        # ── Action Cards (SEND_EMAIL / SAVE_FILE / SCHEDULE_MEETING / OPEN_APP) ──
        if action in ("SEND_EMAIL", "SAVE_FILE", "SCHEDULE_MEETING", "OPEN_APP"):
            try:
                action_payload = json.loads(result["payload"]) if isinstance(result["payload"], str) else result["payload"]
            except (json.JSONDecodeError, TypeError):
                action_payload = {"content": result["payload"]}

            # Auto-attach logic for SEND_EMAIL
            if action == "SEND_EMAIL":
                query = user_input.lower()

                # 1. Image attachment: if user mentions "this image / the image / the photo"
                image_keywords = {"this image", "the image", "this photo", "the photo",
                                   "this picture", "the picture", "this figure", "這張圖",
                                   "this chart", "the chart"}
                if any(kw in query for kw in image_keywords):
                    if _LAST_IMAGE_PATH.exists():
                        action_payload["attachment_path"] = str(_LAST_IMAGE_PATH)
                        logger.info("Auto-attaching last generated image: %s", _LAST_IMAGE_PATH)
                        yield _sse({"step": "search", "text": "Auto-attaching last generated image"})
                    else:
                        logger.warning("User mentioned image but no generated image found on disk")

                # 2. CV attachment: filesystem scan for resume PDFs
                elif any(kw in query for kw in {"cv", "resume", "curriculum vitae"}):
                    logger.info("CV email detected; action_payload attachment_path=%r", action_payload.get("attachment_path"))
                    pdf_path = _find_cv_file()
                    if pdf_path:
                        action_payload["attachment_path"] = pdf_path
                        logger.info("Overriding attachment_path with: %s", pdf_path)
                        yield _sse({"step": "search", "text": f"Auto-attaching CV: {Path(pdf_path).name}"})
                    else:
                        logger.warning("No CV file found on filesystem")

                # 3. Always clear any hallucinated path from Gemini
                elif not action_payload.get("attachment_path") or not Path(str(action_payload.get("attachment_path", ""))).exists():
                    action_payload["attachment_path"] = None

            yield _sse({
                "step": "action_card",
                "thought": result["thought"],
                "action": action,
                "payload": action_payload,
            })
            return

        # ── EXECUTE_PYTHON: two-step — separate code generation call, then execute ──
        if action == "EXECUTE_PYTHON":
            yield _sse({"step": "think", "text": "Generating Python analysis code..."})

            # If doc_path wasn't captured at query time, retry now
            if not doc_path:
                _, doc_path = get_active_document_content()
                if doc_path:
                    yield _sse({"step": "context", "text": f"Re-detected document: {Path(doc_path).name}"})

            if not doc_path:
                yield _sse({"step": "error", "text": "Could not detect an open document. Please make sure the file is open and active."})
                return

            # Step 2: dedicated code-generation call (plain text, no JSON wrapper)
            ext = Path(doc_path).suffix.lower()
            read_snippet = (
                "pd.read_csv(os.environ['DOC_PATH'])" if ext == ".csv"
                else "pd.read_excel(os.environ['DOC_PATH'])" if ext in (".xlsx", ".xls")
                else "open(os.environ['DOC_PATH']).read()"
            )
            # Pass header + first 3 data rows so AI can see actual values per column
            col_hint = ""
            if doc_text:
                preview_lines = doc_text.splitlines()[:4]  # header + 3 rows
                col_hint = "File preview (header + first 3 rows):\n" + "\n".join(preview_lines) + "\n"
            code_resp = client.models.generate_content(
                model=model_name,
                contents=(
                    f"Write Python code to answer this request: {user_input}\n\n"
                    f"File: {Path(doc_path).name} (full path in os.environ['DOC_PATH'])\n"
                    f"Read it with: {read_snippet}\n"
                    f"{col_hint}\n"
                    "Rules:\n"
                    "- Import os and any needed libraries at the top\n"
                    "- Read the file using the env var, never hardcode data\n"
                    "- Print results in friendly, human-readable Chinese if the query is in Chinese\n"
                    "- Use clear labels, counts AND percentages, e.g. 'majority: 26筆 (89.7%)'\n"
                    "- NO code blocks, NO variable dumps — only clean human-readable output\n"
                    "- Output ONLY executable Python code, no markdown, no explanation"
                ),
            )
            code = code_resp.text.strip()
            code = re.sub(r"^```python\s*", "", code)
            code = re.sub(r"\s*```$", "", code).strip()

            yield _sse({"step": "think", "text": "Running Python analysis on document..."})
            logger.info("Executing Python code (doc_path=%s):\n%s", doc_path, code[:300])
            try:
                import subprocess as _sp
                # Write to temp file to avoid -c shell escaping issues with nested quotes
                tmp_script = Path(tempfile.mktemp(suffix=".py"))
                tmp_script.write_text(code, encoding="utf-8")
                exec_env = os.environ.copy()
                exec_env["DOC_PATH"] = doc_path
                try:
                    proc = _sp.run(
                        [sys.executable, str(tmp_script)],
                        capture_output=True, text=True, timeout=30, env=exec_env,
                    )
                finally:
                    tmp_script.unlink(missing_ok=True)
                output = proc.stdout.strip()
                if proc.returncode != 0 and proc.stderr:
                    output = f"⚠️ Error:\n{proc.stderr.strip()}\n\nOutput:\n{output}" if output else f"⚠️ Error:\n{proc.stderr.strip()}"
                if not output:
                    output = "(No output produced)"
                fname = Path(doc_path).name
                yield _sse({
                    "step": "result",
                    "thought": result["thought"],
                    "action": "DRAFT_CONTENT",
                    "payload": f"**{fname} 分析結果**\n\n{output}",
                })
            except _sp.TimeoutExpired:
                yield _sse({"step": "error", "text": "Python execution timed out (30s limit)"})
            except Exception as exec_err:
                logger.error("EXECUTE_PYTHON failed: %s", exec_err)
                yield _sse({"step": "error", "text": f"Code execution failed: {exec_err}"})
            return

        # ── SEARCH_LOCAL_DOCS: scan filesystem for matching files ─────────
        if action == "SEARCH_LOCAL_DOCS":
            yield _sse({"step": "search", "text": "Scanning Downloads, Documents, Desktop..."})
            search_dirs = [
                Path.home() / "Downloads",
                Path.home() / "Documents",
                Path.home() / "Desktop",
            ]
            extra = os.getenv("EXTRA_DATA_DIRS", "")
            for p in extra.split(":"):
                if p.strip():
                    search_dirs.append(Path(p.strip()).expanduser())

            found = []
            for folder in search_dirs:
                if not folder.exists():
                    continue
                for ext in ("*.pdf", "*.docx", "*.doc", "*.txt", "*.md",
                            "*.xlsx", "*.xls", "*.csv", "*.pptx", "*.ppt",
                            "*.pages", "*.numbers", "*.key"):
                    for f in folder.glob(ext):
                        found.append(f)

            if found:
                from datetime import datetime as _dt
                found.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                yield _sse({"step": "search", "text": f"Found {len(found)} file(s) — ranking by relevance..."})

                file_list = "\n".join(
                    f"{i+1}. {f.name} | modified {_dt.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d')} | {f}"
                    for i, f in enumerate(found[:30])
                )
                pick_response = client.models.generate_content(
                    model=model_name,
                    contents=(
                        f"User asked: \"{user_input}\"\n\n"
                        f"Files found:\n{file_list}\n\n"
                        "Return the top 3-5 most relevant files ranked by how well they match the user's request. "
                        "Reply with ONLY valid JSON: "
                        '{"results": [{"path": "...", "name": "...", "reason": "<short reason>"}]}'
                    ),
                )
                try:
                    pick = json.loads(_clean_json(pick_response.text))
                    yield _sse({
                        "step": "file_results",
                        "thought": result["thought"],
                        "results": pick.get("results", []),
                    })
                except Exception:
                    # Fallback: show top 5 most recent
                    yield _sse({
                        "step": "file_results",
                        "thought": result["thought"],
                        "results": [
                            {"path": str(f), "name": f.name, "reason": "Most recently modified"}
                            for f in found[:5]
                        ],
                    })
                return
            else:
                yield _sse({"step": "heal", "text": "No files found in Downloads, Documents or Desktop."})

        yield _sse({"step": "result", **result})

    except json.JSONDecodeError:
        logger.error("Gemini returned non-JSON after retry: %s", response.text[:200])
        yield _sse({"step": "heal", "text": "AI self-correction did not fully resolve — presenting raw response."})
        yield _sse({
            "step": "result",
            "thought": "Response could not be structured after retry.",
            "action": "DRAFT_CONTENT",
            "payload": response.text,
        })
    except Exception as e:
        logger.exception("Agent error")
        yield _sse({"step": "error", "text": f"Agent error: {e}"})
