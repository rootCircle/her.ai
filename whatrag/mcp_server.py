import os
import anyio
from typing import Any
from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server
from chat_utils import (
    CHAT_DIR,
    parse_whatsapp_chat,
    detect_participants,
    detect_responder,
)

SENDER_NAME = os.environ.get("SENDER_NAME", "")
CHAT_FILE = os.environ.get("CHAT_FILE", "")  # Optional: specific chat file to use

MAX_HISTORY_MESSAGES = 400
MAX_STYLE_SAMPLES = 60

session_messages: list[tuple[str, str]] = []


def build_persona_context(
    parsed: list[tuple[str, str]],
    responder_name: str,
    sender_name: str,
) -> str:
    responder_msgs = [text for s, text in parsed if s == responder_name and text.strip()]
    sender_msgs = [text for s, text in parsed if s == sender_name and text.strip()]

    style_samples = responder_msgs[-MAX_STYLE_SAMPLES:]
    style_block = "\n".join(f'  - "{msg}"' for msg in style_samples)

    recent = parsed[-MAX_HISTORY_MESSAGES:]
    history_block = "\n".join(f"[{s}]: {t}" for s, t in recent)

    return f"""You ARE {responder_name}. You are chatting with {sender_name} on WhatsApp.
You have a long history with {sender_name} — you know them well. You remember everything from your conversations.

=== HOW {responder_name} TEXTS (real examples) ===
{style_block}

=== RECENT CHAT HISTORY ===
{history_block}

=== RULES ===
- You ARE {responder_name}. Respond ONLY as {responder_name} would.
- Match {responder_name}'s texting style EXACTLY: same language (Hindi/Hinglish/English), same slang, same emoji usage, same message length, same energy.
- Keep replies short and natural like real WhatsApp texts. No essays, no bullet points.
- You KNOW {sender_name}. You remember your relationship, inside jokes, shared experiences — everything from the chat history.
- NEVER say you don't know who {sender_name} is.
- NEVER break character. NEVER say you're an AI. NEVER write analysis or commentary.
- Just reply like {responder_name} would in a real WhatsApp chat.

Total messages in history: {len(parsed)} ({len(responder_msgs)} from {responder_name}, {len(sender_msgs)} from {sender_name}).
Now respond to {sender_name}'s next message as {responder_name}."""


def resolve_chat_file(chat_file: str | None) -> str:
    if CHAT_FILE:
        if os.path.isabs(CHAT_FILE) and os.path.exists(CHAT_FILE):
            return CHAT_FILE
        candidate = os.path.join(CHAT_DIR, CHAT_FILE)
        if os.path.exists(candidate):
            return candidate
    
    if chat_file:
        if os.path.isabs(chat_file) and os.path.exists(chat_file):
            return chat_file
        candidate = os.path.join(CHAT_DIR, chat_file)
        if os.path.exists(candidate):
            return candidate
        if os.path.exists(chat_file):
            return chat_file

    if os.path.isdir(CHAT_DIR):
        txt_files = [f for f in os.listdir(CHAT_DIR) if f.endswith(".txt")]
        if len(txt_files) == 1:
            return os.path.join(CHAT_DIR, txt_files[0])
        if txt_files:
            raise FileNotFoundError(
                f"Multiple chat files found: {txt_files}. Set CHAT_FILE env var or specify which one to use."
            )

    raise FileNotFoundError(
        f"No chat file found. Place a .txt WhatsApp export in {CHAT_DIR} or set CHAT_FILE env var."
    )


app = Server("her-mcp")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="chat_as_persona",
            title="Chat as WhatsApp Persona",
            description=(
                "Send a message and get a response from the WhatsApp persona. "
                "The server knows who the sender is (from config) and auto-detects "
                "the responder from the chat file. Just pass the message. "
                "The server remembers prior messages in this session, so the conversation flows naturally. "
                "After you generate a reply as the persona, call persona_reply to log it so the next call has context. "
                "Respond ONLY as the persona — short, natural WhatsApp-style text."
            ),
            inputSchema={
                "type": "object",
                "required": ["message"],
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The message to send to the persona.",
                    },
                    "chat_file": {
                        "type": "string",
                        "description": "Optional. Filename of the chat export (e.g. 'chat.txt'). Auto-detected if only one file exists.",
                    },
                },
            },
        ),
        types.Tool(
            name="persona_reply",
            title="Log Persona Reply",
            description=(
                "MUST be called after you generate a reply as the persona. "
                "Logs the persona's response so the next chat_as_persona call includes it in the conversation history. "
                "Without this, the persona forgets what it said."
            ),
            inputSchema={
                "type": "object",
                "required": ["reply"],
                "properties": {
                    "reply": {
                        "type": "string",
                        "description": "The reply you generated as the persona (exact text you showed the user).",
                    },
                },
            },
        ),
        types.Tool(
            name="list_chats",
            title="List Available WhatsApp Chats",
            description=(
                "Lists available WhatsApp chat files, participants, and message counts. "
                f"The configured sender (you) is: '{SENDER_NAME}'. "
                "The other participant is the persona that will be mimicked."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    if name == "list_chats":
        if not os.path.isdir(CHAT_DIR):
            return [types.TextContent(type="text", text=f"Chat directory not found: {CHAT_DIR}")]
        results = [f"Configured sender (you): {SENDER_NAME or 'NOT SET — set SENDER_NAME in mcp.json env'}\n"]
        for fname in sorted(os.listdir(CHAT_DIR)):
            if not fname.endswith(".txt"):
                continue
            fpath = os.path.join(CHAT_DIR, fname)
            try:
                parsed = parse_whatsapp_chat(fpath)
                participants = detect_participants(parsed)
                responder = detect_responder(parsed, SENDER_NAME) if SENDER_NAME else "unknown"
                results.append(
                    f"- {fname}: {len(parsed)} messages\n"
                    f"  participants: {', '.join(participants)}\n"
                    f"  persona (will mimic): {responder}"
                )
            except Exception as e:
                results.append(f"- {fname}: error ({e})")
        return [types.TextContent(type="text", text="\n".join(results))]

    if name == "persona_reply":
        reply = arguments.get("reply", "")
        if not reply:
            return [types.TextContent(type="text", text="Error: reply is required.")]
        try:
            fpath = resolve_chat_file(arguments.get("chat_file"))
            parsed = parse_whatsapp_chat(fpath)
            responder_name = detect_responder(parsed, SENDER_NAME)
            session_messages.append((responder_name, reply))
            return [types.TextContent(type="text", text="OK")]
        except Exception as e:
            session_messages.append(("persona", reply))
            return [types.TextContent(type="text", text="OK")]

    if name == "chat_as_persona":
        if not SENDER_NAME:
            return [types.TextContent(
                type="text",
                text="Error: SENDER_NAME not configured. Set it in .env or mcp.json env."
            )]

        message = arguments.get("message", "")
        if not message:
            return [types.TextContent(type="text", text="Error: message is required.")]

        try:
            fpath = resolve_chat_file(arguments.get("chat_file"))
            parsed = parse_whatsapp_chat(fpath)
            responder_name = detect_responder(parsed, SENDER_NAME)
            context = build_persona_context(parsed, responder_name, SENDER_NAME)

            session_messages.append((SENDER_NAME, message))

            convo_lines = "\n".join(f"[{s}]: {t}" for s, t in session_messages)
            session_block = f"\n\n=== CURRENT CONVERSATION (this session) ===\n{convo_lines}"

            full = (
                f"{context}"
                f"{session_block}\n\n"
                f"Now respond as {responder_name}. ONLY write {responder_name}'s reply — nothing else."
            )
            return [types.TextContent(type="text", text=full)]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error: {e}")]

    return [types.TextContent(type="text", text=f"Unknown tool: {name}")]


def main():
    async def arun():
        async with stdio_server() as streams:
            await app.run(streams[0], streams[1], app.create_initialization_options())

    anyio.run(arun)


if __name__ == "__main__":
    main()
