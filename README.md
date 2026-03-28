# Project Copilot — Microsoft Copilot Demo

An AI-powered desktop assistant built with Electron + React + Python, styled after Microsoft Copilot. Demonstrates a full agentic workflow: RAG over local documents, screen context reading, image generation, email sending, and multi-turn conversation — all streamed in real time.

---

## Features

| Feature | Description |
|---------|-------------|
| **Screen Awareness** | Captures the desktop screenshot and sends it to Gemini so the model can "see" what app you are working in |
| **Local RAG** | Indexes your PDF / TXT files into a vector store and retrieves relevant content via semantic search |
| **Image Generation** | Calls Gemini Image Model with an auto-enhanced prompt and displays the result inline |
| **Email Sending** | Drafts a complete email, auto-attaches your CV or last generated image, and sends it via SMTP |
| **Multi-turn Memory** | Maintains conversation context across messages and persists chats to disk (`~/.copilot/chats/`) |
| **Conversation Sidebar** | Create, switch, rename, and delete conversations; AI auto-generates a title from the first message |
| **Dual UI Mode** | User Mode (clean Copilot-style chat bubbles) / Demo Mode (full agent pipeline log) |

---

## Tech Stack

**Frontend**
- Electron + React + Vite
- Custom CSS (Microsoft Fluent Design inspired)

**Backend**
- FastAPI (Python 3.12) — SSE streaming responses
- Gemini 2.5 Flash — decision-making + multimodal (text + screenshot)
- Gemini Image Model — image generation
- ChromaDB + `sentence-transformers/all-MiniLM-L6-v2` — local vector search
- LangChain — PDF / TXT parsing and chunking

---

## Prerequisites

- Node.js 18+
- Python 3.10–3.12 (3.13 not yet supported by ChromaDB)
- Gemini API Key — [Google AI Studio](https://aistudio.google.com/)
- macOS: grant **Screen Recording** permission to Terminal (System Settings → Privacy & Security → Screen Recording)

---

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

```
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

### 3. Add local knowledge base documents (optional)

Drop any PDF or TXT files into `server/local_data/`. They will be indexed automatically on startup.

---

## Running

Open two terminals:

**Terminal 1 — Python Sidecar**
```bash
cd server
bash start.sh
```

**Terminal 2 — Electron App**
```bash
npm run dev
```

---

## Project Structure

```
Microsoft-copilot-demo/
├── electron/                   # Electron main process
├── src/
│   ├── components/
│   │   ├── CommandPalette.jsx  # Main component: sidebar + conversation management
│   │   ├── AgentThoughts.jsx   # Message rendering (User / Demo dual mode)
│   │   ├── ActionCard.jsx      # Email / save file confirmation card
│   │   └── SearchInput.jsx     # Input bar
│   └── styles/
│       └── index.css
└── server/
    ├── main.py                 # FastAPI routes
    ├── agent.py                # Gemini agent pipeline (SSE streaming)
    ├── chats.py                # Chat persistence (~/.copilot/chats/)
    ├── window_context.py       # Screen capture + foreground app detection
    ├── email_sender.py         # SMTP email sending
    ├── rag/
    │   ├── indexer.py          # Document vectorization
    │   └── searcher.py         # Semantic search
    └── local_data/             # Place your PDF / TXT files here
```

---

## Agent Pipeline

Every time the user sends a message, the backend runs the following steps:

```
1. Detect the foreground application name
2. Capture the desktop screenshot (hide Copilot → capture → restore)
3. Run semantic search over local documents (RAG)
4. Call Gemini multimodal with text + screenshot + conversation history
5. Execute the chosen action: DRAFT_CONTENT / GENERATE_IMAGE / SEND_EMAIL / SAVE_FILE
6. Stream results back to the frontend via SSE
7. Persist the conversation to disk; auto-generate a title on the first message
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | — | Required. Your Google Gemini API key |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model for decision-making |
| `GEMINI_IMAGE_MODEL` | `gemini-3.1-flash-image-preview` | Gemini model for image generation |
| `SMTP_HOST` | — | SMTP server for email sending |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USER` | — | SMTP username / email address |
| `SMTP_PASS` | — | SMTP password or app password |
| `EXTRA_DATA_DIRS` | — | Colon-separated extra directories to scan for CV files |
