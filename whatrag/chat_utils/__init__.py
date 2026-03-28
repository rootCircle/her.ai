"""Shared utilities for WhatsApp chat parsing and processing."""
import os
import re

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHAT_DIR = os.path.join(PROJECT_ROOT, "chat_files")

SKIP_PHRASES = {
    "<media omitted>",
    "you deleted this message",
    "this message was deleted",
    "messages and calls are end-to-end encrypted",
    "null",
}


def parse_whatsapp_chat(filepath: str) -> list[tuple[str, str]]:
    """Parse WhatsApp chat file directly.
    
    Expected format (after Rust parser conversion):
        date, time AM/PM - sender: message
    
    To convert from square bracket format, use the Rust parser:
        cargo run --release --bin langchain_parser "input.txt" > "output.txt"
    """
    messages: list[tuple[str, str]] = []
    
    pattern = re.compile(r'^[\d/]+,\s+[\d:]+\s+[ap]m\s+-\s+([^:]+):\s*(.+)$', re.IGNORECASE)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
                
            match = pattern.match(line)
            if not match:
                continue
                
            sender = match.group(1).strip()
            text = match.group(2).strip()
            
            # Skip unwanted messages
            if not sender or not text or any(skip in text.lower() for skip in SKIP_PHRASES):
                continue
            
            messages.append((sender, text))
    
    return messages


def detect_participants(parsed: list[tuple[str, str]]) -> list[str]:
    """Get list of participants sorted by message count."""
    seen: dict[str, int] = {}
    for sender, _ in parsed:
        seen[sender] = seen.get(sender, 0) + 1
    return sorted(seen.keys(), key=lambda k: seen[k], reverse=True)


def detect_responder(parsed: list[tuple[str, str]], sender_name: str) -> str:
    """The responder is whoever in the chat is NOT the sender."""
    participants = detect_participants(parsed)
    others = [p for p in participants if p != sender_name]
    if not others:
        raise ValueError(
            f"Could not find a responder. SENDER_NAME='{sender_name}' "
            f"but participants are: {participants}"
        )
    return others[0]


__all__ = [
    "CHAT_DIR",
    "SKIP_PHRASES",
    "parse_whatsapp_chat",
    "detect_participants",
    "detect_responder",
]
