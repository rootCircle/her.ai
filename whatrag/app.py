from langchain_community.chat_loaders.whatsapp import WhatsAppChatLoader
from typing import List

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_loaders.base import ChatSession
from langchain_community.chat_loaders.utils import (
    map_ai_messages,
    merge_chat_runs,
)
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.llms import Ollama


loader = WhatsAppChatLoader(
    path="./chat2.txt",
)

raw_messages = loader.lazy_load()
# Merge consecutive messages from the same sender into a single message
merged_messages = merge_chat_runs(raw_messages)
# Convert messages from "Dr. Feather" to AI messages
messages: List[ChatSession] = list(
    map_ai_messages(merged_messages, sender="Saket (TSEC, CS)")
)

# print(messages)

# llm = ChatGoogleGenerativeAI(
#     model="gemini-pro",
#     convert_system_message_to_human=True,
#     client=None,
#     client_options=None,
#     transport=None,
# )


llm = Ollama(model="orca-mini:3b")

messages_raw = messages[0]["messages"]
messages_raw.insert(0, SystemMessage(content="Here is a conversation between two people. Based on these convesation ID these two peoples, their character, persona, likes, dislikes, events in life, mutual relationship etc etc. DON'T CONTINUE THE CONVERSATION, JUST GENERATE INSIGHTS FROM IT!"))
messages_raw.append(
    HumanMessage(
        content=input("Prompt: "),
        additional_kwargs={
            "sender": "Tanay Kamath (TSEC, CS)",
            "events": [{"message_time": "4/23/24, 9:12:43 AM"}],
        },
        role="Tanay Kamath (TSEC, CS)",
    )
)


for chunks in llm.stream(messages_raw):
    print(chunks, end="")

# print(llm.invoke(messages[0]["messages"]))
# print(llm.invoke(messages_raw[:11]).content)
