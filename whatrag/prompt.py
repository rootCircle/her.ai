import time
from langchain_community.chat_loaders.whatsapp import WhatsAppChatLoader
from langchain_community.chat_loaders.utils import map_ai_messages, merge_chat_runs
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import (
    ChatGoogleGenerativeAI,
    HarmBlockThreshold,
    HarmCategory,
)
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
# Define constants for various parameters
SENDER_NAME = "Himan >_<"
RESPONDER_NAME = "her_name"
CHAT_FILENAME = "./Whatsapp_Chats/chate.txt"
MODEL_NAME = "gemini-2.0-flash-exp"
TEMPERATURE = 0

# Initialize the LLM with Gemini model
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
    # max_retries=2,
)

# Load WhatsApp chat using the defined filename
loader = WhatsAppChatLoader(path=CHAT_FILENAME)
raw_messages = loader.lazy_load()

# Merge consecutive messages from the same sender and convert them to AI messages
merged_messages = merge_chat_runs(raw_messages)
messages = list(map_ai_messages(merged_messages, sender=RESPONDER_NAME))

# Initialize the conversation context
messages_raw = messages[0]["messages"]
messages_raw.insert(
    0,
    SystemMessage(
        content=f"""You are a participant in a WhatsApp chat between {SENDER_NAME} and {RESPONDER_NAME}. 
    Your role is to analyze and simulate a natural conversation between these two individuals. You should generate responses 
    that reflect the tone, personality, and context of a typical WhatsApp chat. Keep the conversation casual, responsive, and engaging, 
    similar to how people communicate in a text-based messaging environment.

    - Focus on the relationship dynamics, the subject matter they discuss, and their personalities.
    - DO NOT continue the conversation beyond the message flow provided. Your task is to generate insights, not to add new dialogue. 
    - When responding, simulate a friendly, professional, and approachable tone.
    """,
    ),
)

# Start the interactive chat
while True:
    # Get current time for message timestamp
    current_time = datetime.now().strftime("%m/%d/%Y, %I:%M:%S %p")

    # Add the user input as a prompt to the conversation
    user_prompt = input(f"{SENDER_NAME}: ")  # Displaying sender's name in the prompt

    if user_prompt.lower() in ["exit", "quit", "bye"]:
        print("Ending the conversation.")
        break

    # Append the user input message along with the current timestamp
    messages_raw.append(
        HumanMessage(
            content=user_prompt,
            additional_kwargs={
                "sender": SENDER_NAME,
                "events": [
                    {"message_time": current_time}
                ],  # Using current time as message_time
            },
            role=SENDER_NAME,
        )
    )
    try:
        # Query Gemini with the updated conversation using langchain
        response = llm.invoke(messages_raw)
    except Exception as e:
        print("Some error")
        print("I will sleep for 10 sec and retry once")
        time.sleep(10)
        response = llm.invoke(messages_raw)
    messages_raw.append(response)

    # Print the response from Gemini
    print(RESPONDER_NAME, ":", response.content)
