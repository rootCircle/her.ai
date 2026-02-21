import os
from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv

# Load environment variables from .env files
load_dotenv()

# Constants
MODEL_NAME = "gpt-4o"  # The LLM model name
WHATSAPP_CHAT_DIR = "./Whatsapp_Chats"  # Directory where WhatsApp chat files are stored
CHAT_FILE_PATTERN = "*.txt"  # File pattern for WhatsApp chat files
CHUNK_SIZE = 5000  # Size of each text chunk
CHUNK_OVERLAP = 400  # Overlap between text chunks
VECTOR_SEARCH_K = 15  # Number of similar chunks to retrieve during search

SENDER_NAME = os.environ.get("SENDER_NAME", "")
RESPONDER_NAME = os.environ.get("RESPONDER_NAME", "")

# Initialize the LLM with model constants
llm = ChatOpenAI(model=MODEL_NAME, temperature=0, max_tokens=None, timeout=None)

# Load documents from WhatsApp chat files
loader = DirectoryLoader(WHATSAPP_CHAT_DIR, glob=CHAT_FILE_PATTERN, loader_cls=TextLoader)
docs = loader.load()

# Split the documents into smaller chunks for efficient processing
text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
splits = text_splitter.split_documents(docs)

# Create a vector store for document embeddings using OpenAI
vectorstore = Chroma.from_documents(documents=splits, embedding=OpenAIEmbeddings())

# Create a retriever for retrieving relevant document chunks
retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": VECTOR_SEARCH_K})

# Initialize the prompt template
custom_rag_prompt = PromptTemplate.from_template("""Use the following pieces of context (which are past conversations between responder and his contacts on WhatsApp) to reply to the message at the end as responder.
Answer based on who is sending the message and responder's most recent chat history with that person.
The name of the person sending the message will be shown at the beginning of the message.
If you don't know the person, just say that you don't have their number saved, don't try to make up a random reply for a stranger.
Use three sentences maximum and keep the answer as close to how responder replies as possible.
Always use an emoji at the end of the answer.

{context}

Message: {messageIn}

Reply:""")

# Helper function to format documents as a string
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# Set up the RAG chain for processing the context and user input
rag_chain = (
    {"context": retriever | format_docs, "messageIn": RunnablePassthrough()}
    | custom_rag_prompt
    | llm
    | StrOutputParser()
)

# Start an interactive loop for the conversation
while True:
    user_input = input(f"You ({SENDER_NAME}): ")
    
    # Exit the loop if user types 'exit' or 'quit'
    if user_input.lower() in ['exit', 'quit']:
        print(f"Goodbye from {SENDER_NAME}!")
        break
    
    # Invoke the RAG chain with the user's message
    response = rag_chain.invoke(user_input)
    
    # Display the response
    print(f"{RESPONDER_NAME}: {response}")
