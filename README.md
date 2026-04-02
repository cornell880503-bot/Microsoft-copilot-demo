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
| **Screenshot-First Context** | Captures the current app window on every request so the model always has visual grounding from the user's live workspace |
| **Document-Aware Context** | Extracts actual text from the open document (PDF, Excel, CSV, Word) and combines it with screenshot context for better reasoning |
| **Proactive Suggestions** | Background monitor tracks the active app and surfaces context-aware action chips shortly after opening Copilot |
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
2. Extract text from the open document when supported
3. Capture the current app window for visual grounding
4. Run semantic search over local documents
5. Call Gemini with screenshot, document content, memory, and conversation history
6. Execute the chosen action
7. Stream results back to the frontend via SSE
8. Persist conversation to disk and generate a title
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
- screenshots are captured for every main query and discarded after OCR / API processing
- temporary screenshot files are deleted immediately after capture
- conversations are stored locally in `~/.copilot/chats/`
- file paths and attachments are resolved locally

## Current Behavior Notes

- the main query path is now screenshot-first: every request includes the current app window as visual context
- when a supported document is open, the system sends both structured document text and the screenshot
- structured calendar data primarily comes from macOS Calendar
- browser-based calendars such as Google Calendar and app-based calendars such as Lark currently rely on screenshot understanding rather than first-party connectors
- demo mode shows pipeline steps, but result cards no longer expose raw model reasoning text

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
