# Project Copilot: Reimagined for Product Strategy and Demo Execution

An AI-powered desktop assistant built with Electron + React + Python, styled after Microsoft Copilot. This repository now combines two layers:

- a working prototype that demonstrates agentic desktop assistance
- a PM-ready product strategy narrative for how Copilot evolves from reactive chat into a proactive AI system

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

Primary segment:

Knowledge workers using Windows and web tools daily.

Key pain points:

- constant context switching across browser, docs, and chat
- repetitive workflows
- lack of persistent AI memory

### Product Thesis

We propose that:

- proactive beats reactive
- context is the moat
- memory drives stickiness

Copilot should surface suggestions without prompting, use OS-level and app-level context to unlock a better user experience, and build long-term personalization that improves retention.

### Success Metrics

North Star Metric:

Tasks successfully completed per user per day.

Supporting Metrics:

- time saved per task
- D7 and D30 retention
- task success rate
- tool invocation accuracy

### Experimentation Approach

We would validate this product direction through:

- A/B testing proactive suggestions versus reactive UX
- measuring engagement uplift from memory features
- evaluating task completion versus baseline Copilot

### Why Microsoft Wins

This approach uniquely benefits from Microsoft's ecosystem:

- Windows as a distribution layer
- Office and Graph data for deep context
- enterprise trust and compliance advantages

## Demo Capabilities

The prototype demonstrates:

- multi-step task execution
- tool usage through external actions and APIs
- context-aware responses
- early exploration of memory integration
- real-time document reading from the active desktop workflow
- local RAG over files
- image generation, email sending, and scheduling actions

## Features

| Feature | Description |
|---------|-------------|
| **Fast Intent Router** | Uses a low-latency routing stage to decide action, screenshot need, and RAG need before the heavier execution path runs |
| **Conditional Visual Context** | Captures the current app window only when the task actually needs visual grounding, instead of forcing screenshots on every request |
| **Document-Aware Context** | Extracts actual text from the open document (PDF, Excel, CSV, Word) and combines it with screenshot context for better reasoning |
| **Numbers Workbook Support** | Reads live Apple Numbers workbooks, exports the active workbook to CSV, and falls back across sheets/tables to find a usable data table |
| **Deterministic Spreadsheet Analytics** | Handles common spreadsheet requests such as key metrics, chart suggestions, and general data analysis through fixed analytics templates instead of freeform codegen |
| **Proactive Suggestions** | Background monitor tracks the active app and surfaces preset quick prompts and context-aware suggestions shortly after opening Copilot |
| **Local RAG** | Indexes PDF and TXT files into a vector store and retrieves relevant content via semantic search |
| **Calendar Screen Reading** | Uses screenshot understanding and OCR-style extraction to answer calendar questions when structured connectors are missing |
| **Semantic File Search** | Searches files by natural language and ranks top candidates with open and email actions |
| **Image Generation** | Calls the Gemini image model with an enhanced prompt and displays the result inline |
| **Email Sending** | Drafts a complete email, auto-attaches a CV or the last generated image, and sends it via SMTP |
| **Schedule Meeting** | Creates a `.ics` calendar event and opens it in the system calendar app |
| **Open App** | Launches a macOS application by name, or opens browser actions through Bing search |
| **Multi-turn Memory** | Maintains conversation context across messages and persists chats to disk |
| **Conversation Sidebar** | Creates, switches, renames, and deletes conversations, with auto-generated titles |
| **Dual UI Mode** | Supports both User Mode and Demo Mode with visible agent pipeline logs |
| **Privacy Modes** | Safe Mode keeps proactive help on low-sensitivity metadata, while Enhanced Mode allows richer screen-derived context with explicit user control |
| **Latency Telemetry** | Shows how many seconds each completed prompt took, making routing and fallback behavior easier to debug in demo mode |
| **Self-healing Errors** | Retries on RAG and Gemini formatting failures with visible fallback behavior |

## Why Microsoft Copilot

This prototype demonstrates the product concept behind Microsoft Copilot. The real moat sits in four layers that are difficult for third-party AI tools to replicate:

### 1. OS-Level Native Integration

Copilot can become part of the operating system itself. With first-party OS APIs and privileged context, it can observe workflows across applications without requiring user setup or hacky workarounds.

### 2. Microsoft Graph as Personal Context

Copilot can use the Microsoft 365 graph as a live, permissioned knowledge graph across:

- Outlook
- Teams
- Calendar
- SharePoint and OneDrive

This goes beyond file-based RAG into identity-aware, org-aware assistance.

### 3. Enterprise Trust at Scale

- data stays within the Microsoft 365 tenant boundary
- Microsoft provides enterprise compliance and governance controls
- admins can manage access, auditability, and policy enforcement

### 4. Massive Distribution

Copilot ships through Windows and Microsoft 365 surfaces. That distribution advantage makes new capabilities immediately reachable without separate onboarding.

## Tech Stack

**Frontend**

- Electron
- React
- Vite

**Backend**

- FastAPI on Python 3.12
- Gemini 2.5 Flash for reasoning and multimodal tasks
- Gemini image model for image generation
- ChromaDB with `sentence-transformers/all-MiniLM-L6-v2` for local vector search
- LangChain for parsing and chunking
- `pypdf`, `openpyxl`, and `python-docx` for document extraction

## Prerequisites

- Node.js 18+
- Python 3.10 to 3.12
- Gemini API key from [Google AI Studio](https://aistudio.google.com/)
- macOS screen recording permission for Terminal

## Setup

### 1. Clone and install frontend dependencies

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
GEMINI_MODEL=gemini-2.5-flash
```

### 3. Add local knowledge base documents (optional)

Drop any PDF or TXT files into `server/local_data/`. They will be indexed automatically on startup.

## Running

Open two terminals.

**Terminal 1: Python sidecar**

```bash
cd server
bash start.sh
```

**Terminal 2: Electron app**

```bash
npm run dev
```

## Project Structure

```text
Microsoft-copilot-demo/
├── demo/                      # Placeholder for standalone demo assets if needed
├── docs/                      # PM-facing strategy and experiment documents
├── electron/                  # Electron main process
├── server/                    # FastAPI backend and agent pipeline
├── src/                       # React frontend
└── README.md
```

## Agent Pipeline

Every time the user sends a message, the backend runs the following steps:

```text
1. Detect the previously active app
2. Run a fast router that decides the action plus whether screenshot and RAG are needed
3. Extract text from the open document when supported
4. Capture the current app window only if the routed intent needs visual grounding
5. Run semantic search only if the routed intent needs local retrieval
6. Call the execution model with the selected context, memory, and conversation history
7. Execute the chosen action or deterministic tool path
8. Stream results and timing back to the frontend via SSE
9. Persist conversation to disk and generate a title
```

## Actions

| Action | Trigger | Behaviour |
|--------|---------|-----------|
| `DRAFT_CONTENT` | Write, summarize, explain, translate | Returns formatted text response |
| `GENERATE_IMAGE` | Create or visualize an image | Calls Gemini image model and saves the result for downstream use |
| `SEND_EMAIL` | Send an email | Opens an action card with editable fields and optional attachments |
| `SAVE_FILE` | Save content to disk | Writes output to `~/Downloads/` |
| `SCHEDULE_MEETING` | Schedule a meeting | Generates an `.ics` file and opens the system calendar |
| `OPEN_APP` | Open an application | Launches an app or browser search |
| `SEARCH_LOCAL_DOCS` | Find a file | Scans local directories and ranks relevant files |

## Privacy

- document text is extracted locally and sent only to the Gemini API
- screenshots are captured only for intents that need visual grounding and are discarded after OCR / API processing
- temporary screenshot files are deleted immediately after capture
- conversations are stored locally in `~/.copilot/chats/`
- file paths and attachments are resolved locally
- proactive assistance supports `Safe` and `Enhanced` privacy modes in the UI

## Current Behavior Notes

- the main query path now uses a fast router first, so screenshot capture and RAG are conditional rather than universal
- spreadsheet-style requests in Numbers, Excel, and CSV contexts can short-circuit into deterministic analytics without freeform Python generation
- when a supported document is open, the system sends structured document text and only adds screenshot context when the routed intent requires it
- structured calendar data primarily comes from macOS Calendar
- browser-based calendars such as Google Calendar and app-based calendars such as Lark currently rely on screenshot understanding rather than first-party connectors
- quick prompts on app open are preset by app/window type, so they do not require an extra model call
- demo mode shows pipeline steps, prompt timing, and fallback behavior, but result cards no longer expose raw model reasoning text

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | none | Required. Gemini API key |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Model for reasoning |
| `GEMINI_IMAGE_MODEL` | `gemini-3.1-flash-image-preview` | Model for image generation |
| `SMTP_HOST` | none | SMTP server |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USER` | none | SMTP username or email |
| `SMTP_PASS` | none | SMTP password or app password |
| `EXTRA_DATA_DIRS` | none | Extra directories to scan |

## Additional Docs

- Product Strategy: [docs/product-strategy.md](docs/product-strategy.md)
- Metrics: [docs/metrics.md](docs/metrics.md)
- System Design: [docs/system-design.md](docs/system-design.md)
- Experiment Plan: [docs/experiment-plan.md](docs/experiment-plan.md)
- Privacy Design: [docs/privacy-design.md](docs/privacy-design.md)
