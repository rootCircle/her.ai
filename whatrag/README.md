## Run

For first time:

```bash
uv sync
cp .sample.env .env
```

Replace the API Key with the real API key in `.env` file.

To run code:

```bash
uv run <filename.py>
```

### RAG using Ollama (Local Only)

```bash
uv run ./rag.py --chat-file ./chat.txt --interactive
```

### RAG using Chroma and OpenAI 

Requires OpenAI API keys

```bash
uv run ./rag_chroma.py
```

### Prompt using Gemini

Requires Gemini API keys

```bash
uv run ./prompt.py
```

