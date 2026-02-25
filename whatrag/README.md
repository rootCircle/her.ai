# whatrag

WhatsApp chat RAG and persona simulation. Uses your exported WhatsApp chat history to create an AI that texts like the other person.

## Setup

```bash
uv sync
cp .sample.env .env
```

Edit `.env` and add your API keys and configuration.

For MCP server setup (Cursor/VS Code), copy the sample MCP config:

```bash
# At project root
# For VS Code
cp .vscode/mcp.sample.json .vscode/mcp.json

# For Cursor
cp .cursor/mcp.sample.json .cursor/mcp.json
```

Edit the copied `mcp.json` and update:

- The absolute path to your `whatrag` directory
- `SENDER_NAME`: Your name as it appears in the chat
- `CHAT_FILE`: (Optional) Specific chat file to use from `chat_files/`. If not set, auto-detects single .txt file

## Approaches

### 1. MCP Server (Cursor IDE)

An MCP server that lets Cursor's built-in LLM role-play as a WhatsApp persona. No external API keys needed — uses Cursor's own model.

**How it works:**

- Parses your WhatsApp chat export
- Builds a rich one-time persona context for session init
- Uses embedding-based RAG (FAISS + Ollama embeddings) for follow-up message retrieval
- Reuses a persisted local FAISS cache so unchanged chats do not re-embed on every restart
- Maintains rolling session memory across messages

**Setup:**

1. Make sure you've completed the main setup steps (see above)

2. Configuration is already in `.vscode/mcp.json` or `.cursor/mcp.json` (copied from `.sample` files)

3. Restart Cursor/VS Code. Type `me: hi` in chat to start talking to the persona.

**Tools exposed:**

- `init_persona_session`: Build rich context once and return `SESSION_ID` for the conversation.
- `chat_as_persona`: Send follow-up messages using `session_id`; returns natural persona prompt context.
- `list_chats`: List available chat files and participants.

**Recommended workflow:**

1. Call `init_persona_session` once and store `SESSION_ID`.
2. For each user message, call `chat_as_persona` with the same `session_id`.
3. Pass `previous_persona_reply` from your prior generated persona response.
4. Use `include_static_context=true` only when you need to re-anchor style.

### MCP Embedding RAG settings

The MCP server uses **embedding-only retrieval** for `RELEVANT PAST CONTEXT`.

Environment variables:

- `RAG_EMBED_MODEL` (default: `qwen3-embedding:4b`)
- `RAG_RETRIEVAL_COUNT` (default: `32`)
- `RAG_VECTOR_SEARCH_K` (default: `48`)
- `RAG_CONTEXT_NEIGHBOR_RADIUS` (default: `1`)
- `RAG_VECTOR_CACHE_DIR` (default: `whatrag/.cache/faiss`)

Notes:

- The FAISS cache key includes chat file path, file mtime, responder, and embedding model.
- Changing those inputs creates a new index; otherwise the cache is reused.
- Ensure Ollama is running and the embedding model is available:

```bash
ollama pull qwen3-embedding:4b
```

### Code layout (current)

- `mcp_server.py`: MCP tools, session flow, prompt building
- `rag/retriever.py`: embedding model init, FAISS index/cache, vector retrieval logic
- `chat_utils/`: chat parsing and participant detection

### 2. Prompt-based (Gemini API)

Direct prompting with full chat history as context. Requires a Gemini API key.

```bash
uv run ./prompt.py
```

### 3. RAG with Ollama (Local)

Local RAG using Ollama + FAISS. No API keys needed, just a running Ollama instance.

```bash
uv run ./rag.py --chat-file ./chat.txt --interactive
```

> The standalone scripts are in `archive/` and are kept for reference; MCP flow is the actively maintained path.

### 4. RAG with OpenAI + Chroma

Cloud-based RAG using OpenAI embeddings and Chroma vector store. Requires an OpenAI API key.

```bash
uv run ./rag_chroma.py
```

## WhatsApp Chat Export

To export a chat from WhatsApp:

1. Open the chat in WhatsApp
2. Tap the three dots menu > More > Export chat
3. Choose "Without media"
4. Save the `.txt` file to `../chat_files/`
