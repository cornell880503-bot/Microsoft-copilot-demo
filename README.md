# Project Copilot: Reimagined for Product Strategy and Demo Execution

An AI-powered desktop assistant built with Electron + React + Python, styled after Microsoft Copilot. This repository combines two layers:

- a working prototype that demonstrates agentic desktop assistance
- a PM-ready product strategy narrative for how Copilot evolves from reactive chat into a proactive AI system

---

## What This Copilot Can Do

### Core Capabilities

| Capability | What it does |
|---|---|
| **Python Document Analysis** | Reads your open Excel / CSV / Word / PDF file and runs real pandas / matplotlib code against it — not a description, actual numbers and charts |
| **Chart & Visualization** | Draws bar charts, pie charts, histograms, scatter plots and saves them to Downloads automatically |
| **Email with Attachment** | Drafts an email, attaches a generated chart or document summary, and sends it via SMTP |
| **Meeting Scheduling** | Creates a `.ics` calendar event from natural language (e.g. "next Monday 10am") and opens it in Calendar |
| **Local RAG** | Indexes PDF, TXT, CSV, Excel, and Word files in Downloads / Documents / Desktop into a vector store and retrieves relevant content via semantic search |
| **Image Generation** | Calls Gemini image model with an auto-enhanced prompt and displays the result inline |
| **Open App / Web Search** | Launches any macOS app by name, or opens a Bing search for anything browser-based |
| **File Save** | Writes any output — tables, summaries, analysis results — to `~/Downloads/` |
| **Proactive Suggestions** | Background monitor watches the active app and surfaces context-aware quick prompts automatically |
| **Multi-turn Memory** | Maintains conversation context across messages; persists all chats to disk |

### Technical Highlights

- **Two-stage routing**: a fast lightweight model first decides the action type, whether a screenshot is needed, and whether RAG is needed — before the heavier execution model runs. This cuts average latency significantly.
- **Conditional visual context**: screenshots are captured only for intents that genuinely need visual grounding, not on every request.
- **Real Python execution**: for document analysis the agent generates executable Python code, runs it in a sandboxed subprocess with a 60-second timeout, and streams the actual output back. If the code errors, it auto-repairs and retries once.
- **Self-healing code**: on execution error, the stderr is fed back to Gemini which rewrites the code and re-runs it automatically.
- **Document-aware context**: extracts live text from the open document (Excel, Numbers, CSV, Word, PDF) and passes column headers and sample rows to guide code generation — so the AI always analyzes the right column.
- **Model fallback**: primary model is `gemini-3-flash-preview`; on 503 overload it falls back to `gemini-2.5-flash` automatically.
- **Privacy modes**: Safe Mode and Enhanced Mode give users control over how much screen context the agent reads.

---

## Product Framing

This project explores the next evolution of AI assistants beyond chat-based interaction, inspired by the vision of Microsoft Copilot.

Instead of a reactive chatbot, this demo proposes a proactive, context-aware Copilot that:

- understands user workflows across applications
- anticipates user needs
- executes multi-step tasks autonomously

### Product Vision

Copilot should evolve from a tool you ask into a system that works alongside you.

We believe the next generation of AI assistants will:

- reduce context switching across apps
- persist memory across sessions
- act, not just respond

### Target Users

Primary segment: knowledge workers using Windows and web tools daily.

Key pain points:

- constant context switching across browser, docs, and chat
- repetitive workflows that AI should handle
- lack of persistent AI memory across sessions

### Product Thesis

- proactive beats reactive
- context is the moat
- memory drives stickiness

Copilot should surface suggestions without prompting, use OS-level and app-level context to unlock a better user experience, and build long-term personalization that improves retention.

### Success Metrics

North Star: tasks successfully completed per user per day.

Supporting metrics:

- time saved per task
- D7 and D30 retention
- task success rate
- tool invocation accuracy

### Why Microsoft Wins

- **Windows as distribution layer** — ships to billions of devices without separate onboarding
- **Microsoft Graph as personal context** — live permissioned data from Outlook, Teams, Calendar, SharePoint, OneDrive
- **Enterprise trust and compliance** — data stays within the M365 tenant boundary; admins control access, auditability, and policy
- **Office deep integration** — first-party API access to Word, Excel, PowerPoint enables capabilities that third-party tools cannot replicate

---

## Tech Stack

**Frontend**
- Electron + React + Vite

**Backend**
- FastAPI on Python 3.12
- Gemini `gemini-3-flash-preview` (primary) + `gemini-2.5-flash` (fallback)
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
git clone https://github.com/cornell880503-bot/Microsoft-copilot-demo
cd Microsoft-copilot-demo
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
2. Fast router decides: action type + whether screenshot and RAG are needed
3. Extract live text from the open document (when supported)
4. Capture current app window only if visual grounding is needed
5. Run semantic search only if local retrieval is needed
6. Call execution model with selected context, memory, and conversation history
7. Execute chosen action — deterministic analytics, Python code, or direct response
8. If Python code errors: auto-repair via stderr → Gemini → re-run
9. Stream results and timing back to frontend via SSE
10. Persist conversation to disk and generate a title
```

---

## Actions

| Action | Trigger | Behaviour |
|--------|---------|-----------|
| `EXECUTE_PYTHON` | Analyze data, draw charts, save tables | Generates and runs real Python code; auto-repairs on error |
| `DRAFT_CONTENT` | Write, summarize, explain, translate | Returns formatted text response |
| `GENERATE_IMAGE` | Create or visualize an image | Calls Gemini image model |
| `SEND_EMAIL` | Send an email | Opens action card with editable fields and optional attachments |
| `SAVE_FILE` | Save content to disk | Writes output to `~/Downloads/` |
| `SCHEDULE_MEETING` | Schedule a meeting | Generates `.ics` file and opens system calendar |
| `OPEN_APP` | Open an application | Launches app or browser search |
| `SEARCH_LOCAL_DOCS` | Find a file | Scans local directories and ranks relevant files |

---

## Features

| Feature | Description |
|---------|-------------|
| **Fast Intent Router** | Low-latency routing stage decides action, screenshot need, and RAG need before the heavy execution path runs |
| **Real Python Code Execution** | Agent writes pandas / matplotlib code, runs it in a subprocess, streams the actual output back |
| **Self-Healing Code** | On execution error, stderr is fed back to Gemini which rewrites and re-runs the code automatically |
| **Chart Generation** | Draws bar charts, pie charts, histograms, scatter plots and saves to Downloads |
| **Conditional Visual Context** | Screenshots captured only when the task needs visual grounding |
| **Document-Aware Context** | Extracts live text from open Excel, Numbers, CSV, Word, PDF files with column-level hints for accurate analysis |
| **Multi-format RAG** | Indexes PDF, TXT, CSV, Excel, Word across Downloads / Documents / Desktop |
| **Numbers Workbook Support** | Reads live Apple Numbers workbooks via CSV export, falls back across sheets/tables |
| **Deterministic Spreadsheet Analytics** | Fast-path for common metrics and data-shape questions without freeform codegen |
| **Proactive Suggestions** | Background monitor surfaces context-aware quick prompts on app open |
| **Calendar Integration** | Reads macOS Calendar for structured events; screenshot understanding for Lark/Google Calendar |
| **Image Generation** | Gemini image model with auto-enhanced prompt, result displayed inline |
| **Email Sending** | Drafts email, auto-attaches chart or document, sends via SMTP |
| **Schedule Meeting** | Natural language → `.ics` → system calendar |
| **Multi-turn Memory** | Conversation context persists across messages and sessions |
| **Conversation Sidebar** | Create, switch, rename, delete conversations with auto-generated titles |
| **Dual UI Mode** | User Mode and Demo Mode (with visible pipeline logs and latency telemetry) |
| **Privacy Modes** | Safe Mode and Enhanced Mode give users control over screen context usage |
| **Model Fallback** | Primary `gemini-3-flash-preview` → fallback `gemini-2.5-flash` on 503 |

---

## Privacy

- document text is extracted locally and sent only to the Gemini API
- screenshots are captured only for intents that need visual grounding and discarded after processing
- temporary files are deleted immediately after use
- conversations are stored locally in `~/.copilot/chats/`
- Python code is executed locally in a sandboxed subprocess
- proactive assistance supports Safe and Enhanced privacy modes

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | required | Gemini API key |
| `GEMINI_MODEL` | `gemini-3-flash-preview` | Primary reasoning model |
| `GEMINI_FALLBACK_MODEL` | `gemini-2.5-flash` | Fallback model on 503 |
| `GEMINI_IMAGE_MODEL` | `gemini-3.1-flash-image-preview` | Image generation model |
| `SMTP_HOST` | none | SMTP server hostname |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USER` | none | SMTP username or email address |
| `SMTP_PASS` | none | SMTP password or app password |
| `EXTRA_DATA_DIRS` | none | Additional directories for RAG indexing |

---

## Project Structure

```
Microsoft-copilot-demo/
├── docs/                      # PM strategy, metrics, experiment plan, privacy design
├── electron/                  # Electron main process
├── server/                    # FastAPI backend and agent pipeline
│   ├── agent.py               # Orchestrator: routing, execution, SSE streaming
│   ├── data_analytics.py      # Deterministic spreadsheet analytics fast path
│   ├── window_context.py      # Active app detection and document extraction
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
