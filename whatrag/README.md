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
- Extracts the other person's texting style (slang, emoji, language, message length)
- Feeds chat history + style examples as context to Cursor's model
- Maintains session memory across messages

**Setup:**

1. Make sure you've completed the main setup steps (see above)

2. Configuration is already in `.vscode/mcp.json` or `.cursor/mcp.json` (copied from `.sample` files)

3. Restart Cursor/VS Code. Type `me: hi` in chat to start talking to the persona.

**Tools exposed:**

| Tool               | Description                                                                  |
|--------------------|------------------------------------------------------------------------------|
| `chat_as_persona`  | Send a message, get persona context back for the LLM to reply in-character   |
| `list_chats`       | List available chat files and participants                                   |

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
