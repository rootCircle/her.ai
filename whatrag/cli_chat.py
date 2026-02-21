import os
import time
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_google_genai import (
    ChatGoogleGenerativeAI,
    HarmBlockThreshold,
    HarmCategory,
)
from dotenv import load_dotenv
from chat_utils import CHAT_DIR, parse_whatsapp_chat, detect_responder

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

SENDER_NAME = os.environ.get("SENDER_NAME", "").strip()
if not SENDER_NAME:
    print("Error: SENDER_NAME environment variable is required.")
    print("Please set it in .env file at project root. Example:")
    print("  SENDER_NAME=YourName")
    exit(1)

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "").strip()
if not GOOGLE_API_KEY:
    print("Error: GOOGLE_API_KEY environment variable is required.")
    print("Please set it in .env file at project root. Example:")
    print("  GOOGLE_API_KEY=your_api_key_here")
    exit(1)

CHAT_FILE = os.environ.get("CHAT_FILE", "").strip()
if not CHAT_FILE:
    print("Error: CHAT_FILE environment variable is required.")
    print("Please set it in .env file at project root. Example:")
    print("  CHAT_FILE=chat_langchain.txt")
    exit(1)

responder_name = os.environ.get("RESPONDER_NAME", "")
CHAT_FILENAME = os.path.join(CHAT_DIR, CHAT_FILE)
MODEL_NAME = "gemini-3-flash-preview"
TEMPERATURE = 0.7
MAX_HISTORY_MESSAGES = 600


def to_langchain_messages(parsed_msgs: list[tuple[str, str]], sender_name: str, responder_name: str) -> list[BaseMessage]:
    lc_messages: list[BaseMessage] = []
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
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    },
)

parsed = parse_whatsapp_chat(CHAT_FILENAME)
print(f"Parsed {len(parsed)} messages from {CHAT_FILE}.")

if len(parsed) == 0:
    print(f"Error: No messages found in {CHAT_FILENAME}")
    print("Make sure the file exists and is in the correct format.")
    print("Expected format: date, time AM/PM - sender: message")
    print("\nYou can change the chat file by setting CHAT_FILE in .env")
    print(f"Current: CHAT_FILE={CHAT_FILE}")
    exit(1)

# Auto-detect responder if not set
if not responder_name and SENDER_NAME:
    responder_name = detect_responder(parsed, SENDER_NAME)
    print(f"Auto-detected responder: {responder_name}")

chat_history = to_langchain_messages(parsed, SENDER_NAME, responder_name)
print(f"Converted {len(chat_history)} messages (from {SENDER_NAME} and {responder_name}).")

if len(chat_history) > MAX_HISTORY_MESSAGES:
    chat_history = chat_history[-MAX_HISTORY_MESSAGES:]
    print(f"Using the most recent {MAX_HISTORY_MESSAGES} messages as context.")

responder_msgs = [m.content for m in chat_history if isinstance(m, AIMessage) and m.content.strip()] # type: ignore
style_samples = "\n".join(f"  - \"{msg}\"" for msg in responder_msgs[-60:]) # type: ignore

system_prompt = f"""You ARE {responder_name}. You are chatting with {SENDER_NAME} on WhatsApp.
You have a long history with {SENDER_NAME} — you know them well. The chat history below is your REAL conversation with them. You remember everything in it.

Here are examples of how YOU ({responder_name}) actually text:
{style_samples}

RULES:
- You ARE {responder_name}. You remember your entire chat history with {SENDER_NAME}. You know who they are, your relationship, your inside jokes, everything.
- Reply EXACTLY how {responder_name} texts — same language (Hindi/Hinglish/English), same slang, same emoji usage, same message length, same energy.
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
    
    # Extract text content from response
    if isinstance(response.content, str): # type: ignore
        reply_text = response.content
    elif isinstance(response.content, list): # type: ignore
        # Extract text from structured content
        reply_text = ""
        for item in response.content: # type: ignore
            if isinstance(item, dict) and item.get("type") == "text": # type: ignore
                reply_text += item.get("text", "") # type: ignore
            elif isinstance(item, str):
                reply_text += item # type: ignore
    else:
        reply_text = str(response.content)
    
    print(f"{responder_name}: {reply_text}")
