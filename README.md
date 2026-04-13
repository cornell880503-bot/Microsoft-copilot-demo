# Sierra Command Center

An AI-powered desktop assistant built with Electron + React + Python, styled after Google's design language and powered by Gemini. This repository combines two layers:

- a working prototype that demonstrates agentic desktop assistance for Google Workspace users
- a PM-ready product strategy narrative for how AI assistants evolve from reactive chat into proactive, action-executing systems

Built as a product demo for Google PM application. The entire prototype was designed and built using vibe coding — no prior React or Electron experience.

---

## What Sierra Can Do

### Core Capabilities

| Capability | What it does |
|---|---|
| **Document Analysis** | Reads your open Excel / CSV / Word / PDF file and runs real pandas / matplotlib code against it — actual numbers and charts, not descriptions |
| **Chart & Visualization** | Draws bar charts, pie charts, histograms, scatter plots and saves them to Downloads automatically |
| **Email with Attachment** | Drafts an email, attaches a generated chart or document summary, and sends it via SMTP (Gmail-compatible) |
| **Meeting Scheduling** | Creates a `.ics` calendar event from natural language (e.g. "next Monday 10am") and opens it in Calendar |
| **Local RAG** | Indexes PDF, TXT, CSV, Excel, and Word files in Downloads / Documents / Desktop into a vector store; newly saved files are indexed immediately in the background |
| **Webpage Summarization** | Fetches and summarizes the active browser tab's content on demand |
| **Image Generation** | Calls Gemini image model with an auto-enhanced prompt and displays the result inline |
| **Open App / Web Search** | Launches any macOS app by name, or opens a browser search for anything |
| **File Save (.docx)** | Writes any output as a real Word document to `~/Downloads/`, with proper headings and bullet formatting |
| **File Delete with RAG ranking** | AI ranks local file candidates by relevance; user selects from a list before deletion |
| **Undo Last Action** | Reverses the last file save, delete, or meeting — with an Undo button on the action card and Cmd+Z shortcut |
| **Proactive Suggestions** | Background monitor watches the active app and surfaces context-aware quick prompts automatically |
| **Multi-turn Memory** | Maintains conversation context across messages; persists all chats to disk |

### Technical Highlights

- **Two-stage Gemini routing**: a fast lightweight model (`gemini-2.5-flash`) first decides the action type and whether screenshot / RAG grounding is needed — before the execution model runs. Cuts average latency significantly.
- **Multi-action orchestration**: the fast router can identify multiple required actions in sequence (e.g., draft content → save file → send email); the execution model chains them automatically with carry-forward context.
- **Conditional visual context**: screenshots and browser page fetches are triggered only when the fast router determines the task needs them — never on every request.
- **Real Python execution**: for document analysis the agent generates executable Python code, runs it in a sandboxed subprocess with a 60-second timeout, and streams the actual output back. If the code errors, it auto-repairs and retries once.
- **Self-healing code**: on execution error, the stderr is fed back to Gemini which rewrites the code and re-runs it automatically.
- **Document-aware context**: extracts live text from the open document (Excel, Numbers, CSV, Word, PDF) and passes column headers and sample rows to guide code generation.
- **Auto-locate files by name**: when the user references a file by name in natural language (including mixed Chinese/English), the agent finds it automatically.
- **Incremental RAG indexing**: newly saved files are indexed into the vector store immediately in a background thread — no restart required.
- **Full-stack Undo**: an `ActionLedger` snapshots file state before every write, delete, or calendar action; undo is one click or Cmd+Z.
- **Real .docx output**: saved documents are written as proper Word files with heading and bullet formatting via `python-docx`.
- **Model fallback**: primary model is `gemini-3-flash-preview`; on 503 overload it falls back to `gemini-2.5-flash` automatically.
- **Demo / User mode**: reasoning traces and pipeline logs are visible in Demo Mode for presentation; hidden in User Mode for a clean consumer experience.

---

## Product Framing

This project explores the next evolution of AI assistants beyond chat-based interaction, using Google's Gemini models as the intelligence layer.

Instead of a reactive chatbot, Sierra proposes a proactive, context-aware assistant that:

- understands user workflows across Google Workspace and native desktop apps
- anticipates user needs based on what's currently open
- executes multi-step tasks autonomously — draft, save, send, schedule — in one command

### Product Vision

AI assistants should evolve from tools you ask into systems that work alongside you.

The next generation will:

- reduce context switching across Gmail, Drive, Docs, Calendar, and Sheets
- persist memory across sessions so users never repeat themselves
- act, not just respond — completing full workflows end-to-end

### Target Users

Primary segment: knowledge workers in Google Workspace environments (G Suite enterprises, SMBs, and power users).

Key pain points:

- constant context switching between Drive, Gmail, Calendar, and Sheets
- repetitive workflows that AI should handle end-to-end
- lack of persistent AI memory across sessions

### Product Thesis

- **Proactive beats reactive** — the most valuable AI moments are when it acts before being asked
- **Context is the moat** — an assistant that knows your files, calendar, and emails delivers irreplaceable value
- **Workspace integration unlocks reach** — Gmail, Drive, Calendar, and Meet are the distribution layer; Sierra lives inside them

### Why This Matters for Google

- **Google Workspace as distribution layer** — 3B+ users across Gmail, Drive, Docs, Sheets without separate onboarding
- **Gemini as the intelligence layer** — native integration with Google's frontier models at every tier
- **Trust and enterprise compliance** — Google Workspace data stays within tenant boundaries; admins control access and auditability
- **Google Cloud as execution substrate** — Cloud Run, Vertex AI, and Workspace APIs enable enterprise-grade deployment at scale

### Success Metrics

North Star: Google Workspace tasks completed via AI per user per day.

Supporting metrics:

- time saved per task (target: 3+ minutes per completed workflow)
- D7 and D30 retention on action completions
- task success rate across action types
- tool invocation accuracy vs. user intent

---

## Tech Stack

**Frontend**
- Electron + React + Vite

**Backend**
- FastAPI on Python 3.12
- Gemini `gemini-3-flash-preview` (primary) + `gemini-2.5-flash` (fast router + fallback)
- Gemini image model for image generation
- ChromaDB + `sentence-transformers/all-MiniLM-L6-v2` for local vector search
- LangChain for document parsing and chunking
- `pandas`, `matplotlib`, `pypdf`, `openpyxl`, `python-docx` for document analysis and visualization

---

## Prerequisites

- Node.js 18+
- Python 3.10–3.12
- Gemini API key from [Google AI Studio](https://aistudio.google.com/)
- macOS screen recording permission for Terminal

---

## Setup

### 1. Clone and install frontend

```bash
git clone https://github.com/cornell880503-bot/microsoft-copilot-demo
cd microsoft-copilot-demo
npm install
```

### 2. Configure the backend

```bash
cd server
```

Create a `.env` file:

```env
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-3-flash-preview
GEMINI_FALLBACK_MODEL=gemini-2.5-flash

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password
```

### 3. Install Python dependencies

```bash
cd server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Add local knowledge base documents (optional)

Drop PDF, TXT, CSV, Excel, or Word files into `server/local_data/`. They will be indexed automatically on startup. The agent also scans `~/Downloads/`, `~/Documents/`, and `~/Desktop/` by default.

---

## Running

**Terminal 1: Python sidecar**

```bash
cd server
bash start.sh
```

**Terminal 2: Electron app**

```bash
npm run dev
```

---

## Agent Pipeline

Every time the user sends a message:

```
1. Detect the previously active app
2. Fast router (gemini-2.5-flash): decide action(s) + whether screenshot and RAG are needed
3. Extract live text from the open document (when supported)
4. Capture current app window only if visual grounding is needed
5. Run semantic search only if local retrieval is needed
6. Call execution model with selected context, memory, and conversation history
7. Execute chosen action — deterministic analytics, Python code, or direct response
8. If Python code errors: auto-repair via stderr → Gemini → re-run
9. For multi-action plans: chain subsequent actions with carry-forward context
10. Stream results and timing back to frontend via SSE
11. Persist conversation and pipeline logs to disk; generate conversation title
```

---

## Actions

| Action | Trigger | Behaviour |
|--------|---------|-----------|
| `EXECUTE_PYTHON` | Analyze data, draw charts, save tables | Generates and runs real Python code; auto-repairs on error |
| `DRAFT_CONTENT` | Write, summarize, explain, translate | Returns formatted text response |
| `GENERATE_IMAGE` | Create or visualize an image | Calls Gemini image model |
| `SEND_EMAIL` | Send an email | Opens action card with editable fields and optional attachments |
| `SAVE_FILE` | Save content to disk | Writes real `.docx` Word file to `~/Downloads/`; indexes immediately; undoable |
| `DELETE_FILE` | Delete a local file | AI ranks candidates from RAG; user picks from list; undoable |
| `SCHEDULE_MEETING` | Schedule a meeting | Generates `.ics` file and opens system calendar; undoable |
| `OPEN_APP` | Open an application | Launches app or browser search |
| `SEARCH_LOCAL_DOCS` | Find a file | Scans local directories and ranks relevant files |
| `UNDO_ACTION` | Undo the last action | Restores file from snapshot or removes created artifact |

---

## Features

| Feature | Description |
|---------|-------------|
| **Two-stage Gemini Routing** | `gemini-2.5-flash` fast router decides action + screenshot + RAG needs before the execution model runs |
| **Multi-action Orchestration** | Fast router can output multiple sequential actions; execution model chains them with carry-forward context |
| **Real Python Code Execution** | Agent writes pandas / matplotlib code, runs it in a subprocess, streams actual output back |
| **Self-Healing Code** | On execution error, stderr is fed back to Gemini which rewrites and re-runs automatically |
| **Chart Generation** | Bar charts, pie charts, histograms, scatter plots saved to Downloads |
| **Conditional Visual Context** | Screenshots and browser fetches triggered only when fast router flags the task as needing them |
| **Webpage Summarization** | Fetches the active browser tab's full text on demand |
| **Document-Aware Context** | Extracts live text from open Excel, Numbers, CSV, Word, PDF with column-level hints |
| **Auto-locate Files** | Extracts filenames from natural language queries (including mixed Chinese/English) and resolves them |
| **Multi-format RAG** | Indexes PDF, TXT, CSV, Excel, Word across Downloads / Documents / Desktop; newly saved files indexed immediately |
| **Numbers Workbook Support** | Reads live Apple Numbers workbooks via CSV export, falls back across sheets/tables |
| **Deterministic Spreadsheet Analytics** | Fast-path for common metrics and data-shape questions without freeform codegen |
| **Real .docx File Output** | Saves Word documents with proper heading and bullet formatting via `python-docx` |
| **File Delete with Candidate Ranking** | RAG ranks the most relevant local files; user selects before deletion |
| **Full-stack Undo** | ActionLedger snapshots state before every write/delete/meeting; Cmd+Z or button restores |
| **Proactive Suggestions** | Background monitor surfaces context-aware quick prompts on app open |
| **Image Generation** | Gemini image model with auto-enhanced prompt, result displayed inline |
| **Email Sending** | Drafts email, auto-attaches chart or document, sends via SMTP (Gmail-compatible) |
| **Schedule Meeting** | Natural language → `.ics` → system calendar |
| **Multi-turn Memory** | Conversation context persists across messages and sessions |
| **Pipeline Log Persistence** | Demo Mode preserves the full CTX/THINK/RAG reasoning trace across app restarts |
| **Conversation Sidebar** | Create, switch, rename, delete conversations with auto-generated titles |
| **Demo / User Mode** | Demo Mode shows reasoning traces and pipeline scores; User Mode presents a clean consumer interface |
| **Privacy Modes** | Safe Mode and Enhanced Mode give users control over screen context usage |
| **Model Fallback** | Primary `gemini-3-flash-preview` → fallback `gemini-2.5-flash` on 503 |

---

## Privacy

- document text is extracted locally and sent only to the Gemini API
- screenshots are captured only for intents that need visual grounding and discarded after processing
- temporary files are deleted immediately after use
- conversations are stored locally in `~/.sierra/chats/`
- Python code is executed locally in a sandboxed subprocess
- proactive assistance supports Safe and Enhanced privacy modes

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | required | Gemini API key from Google AI Studio |
| `GEMINI_MODEL` | `gemini-3-flash-preview` | Primary reasoning model |
| `GEMINI_FALLBACK_MODEL` | `gemini-2.5-flash` | Fallback model on 503 |
| `GEMINI_IMAGE_MODEL` | `gemini-3.1-flash-image-preview` | Image generation model |
| `SMTP_HOST` | none | SMTP server hostname (e.g. `smtp.gmail.com`) |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USER` | none | Gmail address |
| `SMTP_PASS` | none | Gmail app password |
| `EXTRA_DATA_DIRS` | none | Additional directories for RAG indexing |

---

## Project Structure

```
sierra-command-center/
├── docs/                      # PM strategy, metrics, experiment plan, privacy design
├── electron/                  # Electron main process
├── server/                    # FastAPI backend and agent pipeline
│   ├── agent.py               # Orchestrator: routing, execution, multi-action, SSE streaming
│   ├── main.py                # FastAPI app, endpoints, action ledger integration
│   ├── action_ledger.py       # Undo system: LIFO snapshot/restore stack
│   ├── data_analytics.py      # Deterministic spreadsheet analytics fast path
│   ├── window_context.py      # Active app detection, document extraction, browser fetch
│   ├── prompt_builder.py      # Context-aware prompt assembly
│   ├── rag/                   # Vector indexer and semantic searcher
│   ├── memory_store.py        # Conversation persistence
│   └── start.sh               # Server startup script
├── src/                       # React frontend
└── README.md
```

---

## Additional Docs

- Product Strategy: [docs/product-strategy.md](docs/product-strategy.md)
- Metrics: [docs/metrics.md](docs/metrics.md)
- System Design: [docs/system-design.md](docs/system-design.md)
- Experiment Plan: [docs/experiment-plan.md](docs/experiment-plan.md)
- Privacy Design: [docs/privacy-design.md](docs/privacy-design.md)
