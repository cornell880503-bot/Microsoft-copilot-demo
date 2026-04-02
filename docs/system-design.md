# System Design (PM-Level)

## Architecture Overview

### 1. Reasoning Layer

The LLM interprets user intent and breaks complex goals into manageable steps.

### 2. Tool Layer

The tool layer executes actions such as search, writing, and API calls.

### 3. Memory Layer

- short-term memory stores session context
- long-term memory stores preferences and history

### 4. UX Layer

- Copilot interface
- proactive suggestion system

## Runtime Pipeline

The current runtime pipeline is optimized around visual grounding.
Every main query now captures the current app window as a screenshot, even when
structured document text is available. This keeps the model aligned with the
user's real screen state instead of relying only on inferred app context.

High-level request flow:

1. detect the active app/window
2. extract document text when a supported file is open
3. capture the current app window as screenshot context
4. run local RAG lookup
5. build the augmented prompt from screenshot, document, memory, and retrieved context
6. call the reasoning model
7. route into direct answer, action card, Python execution, image generation, or file search

## Context Strategy

The system now uses a dual-context approach:

- visual context from a fresh screenshot on every turn
- structured context from document extraction, local calendar, memory, and local RAG

This is intentionally redundant. Structured data is more reliable when available,
but screenshots are often the fastest way to ground the model in what the user
is actually looking at.

## Tool Orchestration Patterns

### General Q&A or UI-Aware Help

- Inputs: active window, screenshot, history
- Pattern: window detection -> screenshot capture -> prompt build -> Gemini response
- Goal: let the model answer based on what is visibly on screen

### Document Summary / Explanation

- Inputs: document text, document path, screenshot
- Pattern: document extraction -> screenshot capture -> prompt build -> Gemini response
- Goal: combine exact file text with the visual state of the current workspace

### Calendar / Meeting Questions

- Inputs: local macOS Calendar events first, then screenshot fallback
- Pattern: local calendar lookup -> screenshot OCR / screenshot interpretation -> Gemini response
- Goal: prefer structured answers when possible, but allow screen-inferred answers when the connector is missing

### Local Knowledge Base Queries

- Inputs: semantic search results, screenshot
- Pattern: local RAG search -> prompt build -> Gemini response
- Goal: use local files when relevant, otherwise fall back to general reasoning

### Email Drafting

- Inputs: email-related context hints, screenshot
- Pattern: context provider -> Gemini draft -> action card -> send-email endpoint
- Goal: generate a ready-to-send draft, then keep execution explicit and confirmable

### Save File

- Inputs: generated content, screenshot
- Pattern: Gemini decides SAVE_FILE -> action card -> save-file endpoint
- Goal: keep the model in charge of the content while the sidecar controls file writes

### Schedule Meeting

- Inputs: query, calendar intent, screenshot
- Pattern: Gemini decides SCHEDULE_MEETING -> action card -> schedule-meeting endpoint
- Goal: draft event fields in-model, but perform the calendar action with deterministic code

### Image Generation

- Inputs: user prompt, active window
- Pattern: prompt augmentation -> image model call -> inline result
- Goal: use current app context to enrich prompt quality before image generation

### Python-Based Analysis

- Inputs: document path, document preview, screenshot
- Pattern: Gemini decides EXECUTE_PYTHON -> dedicated code generation -> subprocess execution -> retry on failure
- Goal: keep numerical/file analysis deterministic by running real code instead of freeform text reasoning

### Proactive Suggestions

- Inputs: active window, optional screen-derived hints in Enhanced mode
- Pattern: context provider -> suggestion engine -> suggestion chips
- Goal: surface likely next actions before the user explicitly asks

## Screenshot Policy

The main query path now captures a screenshot on every request.
The screenshot is used as transient model input and is not persisted as product data.
Temporary files are deleted immediately after capture and OCR/vision processing.

This policy trades some extra latency for better grounding, especially in:

- browser-based workflows such as Google Calendar
- chat tools such as Lark or Feishu
- complex desktop layouts where app name alone is too coarse

## Known Limitations

- structured calendar support still primarily comes from macOS Calendar
- Lark and Google Calendar are currently handled through screenshot understanding rather than first-party connectors
- screenshot-driven answers may still be less reliable than structured integrations
- proactive suggestions are not yet fully aligned with the new always-capture strategy

## Key Tradeoffs

- latency versus capability
- privacy versus personalization
- autonomy versus user control
