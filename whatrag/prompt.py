from langchain_community.chat_loaders.whatsapp import WhatsAppChatLoader
from langchain_community.chat_loaders.utils import map_ai_messages, merge_chat_runs
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.llms import Ollama

# Load WhatsApp chat
loader = WhatsAppChatLoader(path="./chat.txt")
raw_messages = loader.lazy_load()

# Merge consecutive messages from the same sender and convert them to AI messages
merged_messages = merge_chat_runs(raw_messages)
messages = list(map_ai_messages(merged_messages, sender="Dr. Feather"))

# Initialize the LLM model
llm = Ollama(model="orca-mini:3b")

# Prepare conversation context
messages_raw = messages[0]["messages"]
messages_raw.insert(
    0, 
    SystemMessage(content="Analyze the conversation and generate insights about the participants: their character, persona, likes, dislikes, events in life, mutual relationship, etc. DO NOT continue the conversation. Just provide insights.")
)

# Add the user input as a prompt to the conversation
user_prompt = input("Prompt: ")
messages_raw.append(
    HumanMessage(
        content=user_prompt,
        additional_kwargs={
            "sender": "Tanay Kamath (TSEC, CS)",
            "events": [{"message_time": "4/23/24, 9:12:43 AM"}],
        },
        role="Tanay Kamath (TSEC, CS)"
    )
)

# Stream the response from the model
for chunk in llm.stream(messages_raw):
    print(chunk, end="")


