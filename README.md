# her.ai

Chat with your WhatsApp contacts as AI personas using their real message history. Integrates with Cursor/VS Code via Model Context Protocol (MCP).

## Overview

her.ai creates AI personas that mimic your WhatsApp contacts' texting styles based on their actual chat history. Use it through:

- **MCP Server** - Chat in Cursor/VS Code with `me: your message` syntax
- **CLI Chat** - Interactive terminal conversations

## Quick Start

### 1. Export Your WhatsApp Chat

On your phone:

1. Open WhatsApp chat
2. Tap ⋮ (menu) → **More** → **Export chat**
3. Choose **Without Media**
4. Save/email the `.txt` file to your computer

### 2. Setup Project

```bash
git clone --recursive https://github.com/rootCircle/her.ai.git
cd her.ai
```

### 3. Convert Chat Format

WhatsApp exports use `[date, time]` format. Convert to LangChain format:

```bash
cd whatsapp_chat_parser
cargo run --release --bin langchain_parser "path/to/WhatsApp Chat.txt" > "../chat_files/chat_converted.txt"
```

### 4. Configure Environment

Copy `.sample.env` to `.env` at project root:

```bash
cp .sample.env .env
```

Edit `.env`:

```bash
SENDER_NAME=YourName              # Your name as it appears in chat
CHAT_FILE=chat_converted.txt      # Converted chat file name
GOOGLE_API_KEY=your_key_here      # For Gemini (only for CLI chat)
```

### 5. Configure MCP (for Cursor/VS Code)

Copy the sample MCP config:

```bash
# For VS Code
cp .vscode/mcp.sample.json .vscode/mcp.json

# For Cursor
cp .cursor/mcp.sample.json .cursor/mcp.json
```

Edit the copied `mcp.json` and update:
- The absolute path to your `her.ai/whatrag` directory
- `SENDER_NAME`: Your name as it appears in the chat
- `CHAT_FILE`: (Optional) Specific chat file to use. If not set, auto-detects single .txt file in chat_files/

### 6. Install Python Dependencies

```bash
cd whatrag
uv sync
```

## Usage

### MCP Server (Cursor/VS Code)

The MCP server is configured in `.vscode/mcp.json` or `.cursor/mcp.json` (copied from `.sample` files):

```json
{
  "mcpServers": {
    "her-mcp": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/her.ai/whatrag", "run", "mcp_server.py"],
      "env": {
        "SENDER_NAME": "YourName",
        "CHAT_FILE": "chat_converted.txt"
      }
    }
  }
}
```

**Usage in chat:**

```
me: hey what's up
```

The AI responds as your contact, matching their style, slang, emoji usage, etc.

### CLI Interactive Chat

```bash
cd whatrag
uv run cli_chat.py
```

Type messages and the AI responds as the detected persona from your chat history.

## Tools

### WhatsApp Chat Parser (Rust)

Located in `whatsapp_chat_parser/`:

- **langchain_parser** - Convert WhatsApp format to LangChain format
- **analysis** - Analyze chat metrics, sentiment, activity patterns
- **token_count** - Count tokens for GPT models
- **finetune_preprocess** - Prepare chat data for LLM fine-tuning

See [whatsapp_chat_parser/README.md](whatsapp_chat_parser/README.md) for details.

## Requirements

- **Rust** (for chat parser)
- **Python 3.11+**
- **uv** (Python package manager)
- **Ollama** (optional, for local RAG)
- **API Keys** (Gemini/OpenAI for LLM access)

## License

See [LICENSE](LICENSE) file.
