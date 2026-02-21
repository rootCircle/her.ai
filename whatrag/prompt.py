import re
import time
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_google_genai import (
    ChatGoogleGenerativeAI,
    HarmBlockThreshold,
    HarmCategory,
)
from dotenv import load_dotenv

load_dotenv()

SENDER_NAME = "Himan >_<"
RESPONDER_NAME = "Komal (PGS)"
CHAT_FILENAME = "./Whatsapp_Chats/chat.txt"
MODEL_NAME = "gemini-2.5-flash"
TEMPERATURE = 0.7
MAX_HISTORY_MESSAGES = 600

MSG_PATTERN = re.compile(
    r"^(\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}\s*[ap]m)\s*-\s*(.+?):\s*(.+)$",
    re.IGNORECASE,
)

SKIP_PHRASES = {
    "<media omitted>",
    "you deleted this message",
    "this message was deleted",
    "messages and calls are end-to-end encrypted",
    "null",
}


def parse_whatsapp_chat(filepath):
    messages = []
    current_sender = None
    current_text = None

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            match = MSG_PATTERN.match(line)
            if match:
                if current_sender and current_text:
                    messages.append((current_sender, current_text.strip()))
                current_sender = match.group(2)
                current_text = match.group(3)
            elif current_sender:
                current_text += "\n" + line

    if current_sender and current_text:
        messages.append((current_sender, current_text.strip()))

    filtered = []
    for sender, text in messages:
        if any(skip in text.lower() for skip in SKIP_PHRASES):
            continue
        filtered.append((sender, text))

    return filtered


def to_langchain_messages(parsed_msgs, sender_name, responder_name):
    lc_messages = []
    for sender, text in parsed_msgs:
        if sender == responder_name:
            lc_messages.append(AIMessage(content=text))
        elif sender == sender_name:
            lc_messages.append(HumanMessage(content=text))
    return lc_messages


llm = ChatGoogleGenerativeAI(
    model=MODEL_NAME,
    temperature=TEMPERATURE,
    max_tokens=None,
    timeout=None,
    safety_settings={
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_TOXICITY: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_UNSPECIFIED: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DEROGATORY: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUAL: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    },
)

parsed = parse_whatsapp_chat(CHAT_FILENAME)
print(f"Parsed {len(parsed)} messages from chat file.")

chat_history = to_langchain_messages(parsed, SENDER_NAME, RESPONDER_NAME)
print(f"Converted {len(chat_history)} messages (from {SENDER_NAME} and {RESPONDER_NAME}).")

if len(chat_history) > MAX_HISTORY_MESSAGES:
    chat_history = chat_history[-MAX_HISTORY_MESSAGES:]
    print(f"Using the most recent {MAX_HISTORY_MESSAGES} messages as context.")

responder_msgs = [m.content for m in chat_history if isinstance(m, AIMessage) and m.content.strip()]
style_samples = "\n".join(f"  - \"{msg}\"" for msg in responder_msgs[-60:])

system_prompt = f"""You ARE {RESPONDER_NAME}. You are chatting with {SENDER_NAME} on WhatsApp.
You have a long history with {SENDER_NAME} — you know them well. The chat history below is your REAL conversation with them. You remember everything in it.

Here are examples of how YOU ({RESPONDER_NAME}) actually text:
{style_samples}

RULES:
- You ARE {RESPONDER_NAME}. You remember your entire chat history with {SENDER_NAME}. You know who they are, your relationship, your inside jokes, everything.
- Reply EXACTLY how {RESPONDER_NAME} texts — same language (Hindi/Hinglish/English), same slang, same emoji usage, same message length, same energy.
- Keep replies short and natural like real WhatsApp texts. No essays.
- NEVER say you don't know who {SENDER_NAME} is. You know them. You've been chatting with them.
- NEVER break character. NEVER say you're an AI. NEVER write analysis or commentary.
- If asked about something from your chat history, recall it naturally like a real person would.
"""

messages_context = [SystemMessage(content=system_prompt)] + chat_history

print(f"\nLoaded {len(chat_history)} messages as context.")
print(f"Ready! You are chatting as {SENDER_NAME}. Type 'exit' to quit.\n")

while True:
    user_prompt = input(f"{SENDER_NAME}: ")

    if user_prompt.lower() in ["exit", "quit", "bye"]:
        print("Ending the conversation.")
        break

    messages_context.append(HumanMessage(content=user_prompt))

    try:
        response = llm.invoke(messages_context)
    except Exception as e:
        print(f"Error: {e}")
        print("Retrying in 10 seconds...")
        time.sleep(10)
        response = llm.invoke(messages_context)

    messages_context.append(response)
    print(f"{RESPONDER_NAME}: {response.content}")
