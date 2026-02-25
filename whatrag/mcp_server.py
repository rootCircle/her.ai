import os
import anyio
import hashlib
from typing import Any
from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server
from rag import EmbeddingRAG, clamp_text
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
FOLLOWUP_HISTORY_MESSAGES = 40
FOLLOWUP_STYLE_SAMPLES = 12
MAX_SESSION_RECENT = 10
MAX_SUMMARY_LINES = 10
MAX_MESSAGE_CHARS = 280

chat_cache: dict[str, dict[str, Any]] = {}
persona_sessions: dict[str, dict[str, Any]] = {}
rag = EmbeddingRAG(max_message_chars=MAX_MESSAGE_CHARS)


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


def build_followup_context(
    parsed: list[tuple[str, str]],
    session: dict[str, Any],
    responder_name: str,
    sender_name: str,
    user_message: str,
    snapshot: dict[str, Any],
    include_static_context: bool,
) -> str:
    responder_msgs = [text for s, text in parsed if s == responder_name and text.strip()]
    style_samples = [clamp_text(text, MAX_MESSAGE_CHARS) for text in responder_msgs[-FOLLOWUP_STYLE_SAMPLES:]]
    style_block = "\n".join(f'  - "{msg}"' for msg in style_samples) or "  - (none)"

    recent = [(s, clamp_text(t, MAX_MESSAGE_CHARS)) for s, t in parsed[-FOLLOWUP_HISTORY_MESSAGES:]]
    history_block = "\n".join(f"[{s}]: {t}" for s, t in recent) or "(none)"

    relevant = rag.relevant_history(snapshot, user_message)
    relevant_block = "\n".join(f"[{s}]: {t}" for s, t in relevant) or "(none)"

    session_recent = session.get("messages", [])
    session_block = "\n".join(f"[{s}]: {clamp_text(t, MAX_MESSAGE_CHARS)}" for s, t in session_recent) or "(none)"
    summary_block = session.get("rolling_summary", "") or "(none)"

    followup = f"""You ARE {responder_name}. Continue the same WhatsApp conversation with {sender_name}.

=== HOW {responder_name} TEXTS (recent real examples) ===
{style_block}

=== RECENT CHAT HISTORY ===
{history_block}

=== RELEVANT PAST CONTEXT ===
{relevant_block}

=== SESSION MEMORY (older turns) ===
{summary_block}

=== CURRENT CONVERSATION (this session) ===
{session_block}

=== RULES ===
- You ARE {responder_name}. Respond ONLY as {responder_name} would.
- Match {responder_name}'s texting style EXACTLY: same language mix, slang, emoji usage, message length, and energy.
- Keep replies short and natural like real WhatsApp texts. No essays, no bullet points.
- NEVER break character. NEVER say you're an AI. NEVER write analysis or commentary.

Now respond to {sender_name}'s next message as {responder_name}. ONLY write {responder_name}'s reply — nothing else."""

    if not include_static_context:
        return followup

    static_context = session.get("static_context", "")
    if not static_context:
        return followup
    return f"{static_context}\n\n=== CONTINUE THE SAME CHAT ===\n{followup}"


def get_chat_snapshot(fpath: str) -> dict[str, Any]:
    mtime = os.path.getmtime(fpath)
    cached = chat_cache.get(fpath)
    if cached and cached.get("mtime") == mtime:
        return cached

    parsed = parse_whatsapp_chat(fpath)
    responder_name = detect_responder(parsed, SENDER_NAME)
    snapshot: dict[str, Any] = {
        "fpath": fpath,
        "mtime": mtime,
        "parsed": parsed,
        "responder_name": responder_name,
        "static_context": build_persona_context(parsed, responder_name, SENDER_NAME),
        "vector_store": None,
        "vector_ready": False,
    }
    chat_cache[fpath] = snapshot
    return snapshot


def get_session_id(fpath: str, responder_name: str, requested_session_id: str | None) -> str:
    if requested_session_id:
        return requested_session_id
    digest = hashlib.sha1(f"{fpath}|{SENDER_NAME}|{responder_name}".encode("utf-8")).hexdigest()[:12]
    return f"session-{digest}"


def get_or_create_session(session_id: str, snapshot: dict[str, Any]) -> dict[str, Any]:
    existing = persona_sessions.get(session_id)
    if existing:
        return existing

    session: dict[str, Any] = {
        "session_id": session_id,
        "responder_name": snapshot["responder_name"],
        "static_context": snapshot["static_context"],
        "messages": [],
        "rolling_summary": "",
        "initialized": False,
    }
    persona_sessions[session_id] = session
    return session


def add_session_message(session: dict[str, Any], sender: str, text: str) -> None:
    cleaned = clamp_text(text, MAX_MESSAGE_CHARS)
    if not cleaned:
        return

    session["messages"].append((sender, cleaned))
    messages: list[tuple[str, str]] = session["messages"]
    if len(messages) <= MAX_SESSION_RECENT:
        return

    overflow = messages[:-MAX_SESSION_RECENT]
    existing_summary = str(session.get("rolling_summary", ""))
    summary_lines: list[str] = existing_summary.splitlines() if existing_summary else []
    summary_lines.extend(f"[{s}]: {clamp_text(t, 120)}" for s, t in overflow)
    session["rolling_summary"] = "\n".join(summary_lines[-MAX_SUMMARY_LINES:])
    session["messages"] = messages[-MAX_SESSION_RECENT:]


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
            name="init_persona_session",
            title="Initialize Persona Session",
            description=(
                "Build the rich persona context once and return a session_id. "
                "Use that session_id in follow-up chat_as_persona calls."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "chat_file": {
                        "type": "string",
                        "description": "Optional. Filename of the chat export (e.g. 'chat.txt'). Auto-detected if only one file exists.",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Optional. Provide your own session id to resume a prior thread.",
                    },
                },
            },
        ),
        types.Tool(
            name="chat_as_persona",
            title="Chat as WhatsApp Persona",
            description=(
                "Send a message and get a natural follow-up persona prompt for WhatsApp-style replies. "
                "For best quality and lower repeated context, call init_persona_session once and reuse its session_id."
            ),
            inputSchema={
                "type": "object",
                "required": ["message"],
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The message to send to the persona.",
                    },
                    "previous_persona_reply": {
                        "type": "string",
                        "description": "The exact reply you generated as the persona in the PREVIOUS turn. Pass this so the server logs it into conversation history. On the first message, omit this.",
                    },
                    "chat_file": {
                        "type": "string",
                        "description": "Optional. Filename of the chat export (e.g. 'chat.txt'). Auto-detected if only one file exists.",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Optional session id. Reuse the id returned by init_persona_session.",
                    },
                    "include_static_context": {
                        "type": "boolean",
                        "description": "Optional. If true, prepends the rich init context again for re-anchoring.",
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
            snapshot = get_chat_snapshot(fpath)
            parsed = snapshot["parsed"]
            responder_name = snapshot["responder_name"]
            session_id = get_session_id(fpath, responder_name, arguments.get("session_id"))
            session = get_or_create_session(session_id, snapshot)

            # Log the previous persona reply into session history if provided
            previous_reply = arguments.get("previous_persona_reply", "")
            if previous_reply:
                add_session_message(session, responder_name, previous_reply)

            add_session_message(session, SENDER_NAME, message)

            include_static = arguments.get("include_static_context")
            if include_static is None:
                include_static = not bool(session.get("initialized", False))

            full = build_followup_context(
                parsed=parsed,
                session=session,
                responder_name=responder_name,
                sender_name=SENDER_NAME,
                user_message=message,
                snapshot=snapshot,
                include_static_context=bool(include_static),
            )
            session["initialized"] = True
            return [types.TextContent(type="text", text=full)]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error: {e}")]

    if name == "init_persona_session":
        if not SENDER_NAME:
            return [types.TextContent(
                type="text",
                text="Error: SENDER_NAME not configured. Set it in .env or mcp.json env."
            )]

        try:
            fpath = resolve_chat_file(arguments.get("chat_file"))
            snapshot = get_chat_snapshot(fpath)
            responder_name = snapshot["responder_name"]
            session_id = get_session_id(fpath, responder_name, arguments.get("session_id"))
            session = get_or_create_session(session_id, snapshot)
            session["initialized"] = True

            return [types.TextContent(
                type="text",
                text=(
                    f"SESSION_ID: {session_id}\n\n"
                    f"{session['static_context']}\n\n"
                    "Use this same SESSION_ID in follow-up chat_as_persona calls."
                ),
            )]
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
