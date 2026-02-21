import argparse
import os
import signal
import sys

from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaLLM
from langchain_ollama import OllamaEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_text_splitters import RecursiveCharacterTextSplitter
from chat_utils import CHAT_DIR, parse_whatsapp_chat, detect_participants

# Load .env from project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# Configuration constants
DEFAULT_MODEL = "llama3.2"
CHUNK_SIZE = 5000
CHUNK_OVERLAP = 400
RETRIEVAL_K = 15


class WhatsAppChatSimulator:
    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        self.llm = OllamaLLM(model=model_name)
        self.embeddings = OllamaEmbeddings(model=model_name)
        self.vector_store = None
        self.participants = set()
        self.selected_participant = None
        self.chat_sessions = []  # Store the loaded chat sessions

    def get_whatsapp_chat(self, chat_file: str) -> list[tuple[str, str]]:
        """Load WhatsApp chat using the shared parser."""
        return parse_whatsapp_chat(chat_file)

    def process_whatsapp_chat(self, chat_file: str):
        """Process chat file and extract participants."""
        messages = self.get_whatsapp_chat(chat_file)
        if not messages:
            print("Error: No messages loaded from the chat file.")
            sys.exit(1)
        
        # Extract unique participants
        self.participants = set(detect_participants(messages))
        self.messages = messages

    def select_participant(self) -> str:
        """Allow user to select which participant to simulate."""
        if not self.participants:
            print("Error: No participants found in chat.")
            sys.exit(1)

        participants = sorted(p for p in self.participants)

        print("\nAvailable participants:")
        for idx, participant in enumerate(participants, 1):
            print(f"{idx}. {participant}")

        while True:
            try:
                choice = input(
                    "\nSelect a participant number to simulate as an AI (or 'q' to quit): "
                )
                if choice.lower() == "q":
                    print("Exiting...")
                    sys.exit(0)

                idx = int(choice) - 1
                if 0 <= idx < len(participants):
                    self.selected_participant = participants[idx]
                    return participants[idx]
                else:
                    print("Invalid selection. Please try again.")
            except ValueError:
                print("Please enter a valid number.")
            except (KeyboardInterrupt, EOFError):
                print("\nExiting...")
                sys.exit(0)

    def create_embeddings(self, messages: list[tuple[str, str]], participant: str, save_path: str):
        """Create and save embeddings for the selected participant's messages."""
        # Filter messages from the selected participant
        participant_texts = [text for sender, text in messages if sender == participant]
        
        if not participant_texts:
            print(f"No messages found for participant: {participant}")
            sys.exit(1)
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
        )
        
        docs = text_splitter.create_documents(participant_texts)

        self.vector_store = FAISS.from_documents(docs, self.embeddings)
        self.vector_store.save_local(save_path)

    def load_embeddings(self, load_path: str):
        """Load existing embeddings from disk."""
        self.vector_store = FAISS.load_local(load_path, self.embeddings)

    def setup_qa_chain(self):
        """Set up the RAG chain for question answering using LCEL."""
        prompt_template = f"""You are simulating {self.selected_participant} based on their WhatsApp messages.
Use the following chat history to understand their writing style, personality, and typical responses:

{{context}}

Based on the chat style above, respond to: {{question}}

Important: You are {self.selected_participant}. Maintain their typical message length, use of emojis, 
slang, and overall communication style as shown in the examples.
Response:"""

        prompt = PromptTemplate(
            template=prompt_template, input_variables=["context", "question"]
        )
        
        retriever = self.vector_store.as_retriever(search_kwargs={"k": RETRIEVAL_K})
        
        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)
        
        # Modern LCEL chain
        chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | prompt
            | self.llm
            | StrOutputParser()
        )

        return chain


def signal_handler(sig, frame):
    print("\nExiting gracefully...")
    sys.exit(0)


def main():
    # Set up signal handler for graceful exit
    signal.signal(signal.SIGINT, signal_handler)

    parser = argparse.ArgumentParser(description="WhatsApp Chat Simulator using RAG")
    parser.add_argument(
        "--chat-file", type=str, help="Path to WhatsApp chat export file (relative to chat_files directory or absolute path)"
    )
    parser.add_argument(
        "--embeddings-dir",
        type=str,
        default="chat_embeddings",
        help="Directory to save/load embeddings",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"Ollama model to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--interactive", action="store_true", help="Start interactive chat mode"
    )

    args = parser.parse_args()
    
    # Validate required argument
    if not args.chat_file:
        print("Error: --chat-file is required")
        parser.print_help()
        sys.exit(1)
    
    # Resolve chat file path
    chat_file_path = args.chat_file
    if not os.path.isabs(chat_file_path):
        chat_file_path = os.path.join(CHAT_DIR, chat_file_path)
    
    if not os.path.exists(chat_file_path):
        print(f"Error: Chat file not found: {chat_file_path}")
        sys.exit(1)

    simulator = WhatsAppChatSimulator(model_name=args.model)

    try:
        # Create embeddings directory if it doesn't exist
        os.makedirs(args.embeddings_dir, exist_ok=True)

        # Process chat file
        print(f"Processing chat file using {args.model}...")
        simulator.process_whatsapp_chat(chat_file_path)

        # Let user select which participant to simulate
        selected_participant = simulator.select_participant()
        print(f"\nSelected participant: {selected_participant}")

        # Create participant-specific embeddings path
        embeddings_path = os.path.join(
            args.embeddings_dir, f"faiss_store_{selected_participant}"
        )
        simulator.create_embeddings(simulator.messages, selected_participant, embeddings_path)
        print("Chat processing complete. Embeddings saved.")

        qa_chain = simulator.setup_qa_chain()

        if args.interactive:
            print(
                f"\nEntering interactive mode as {simulator.selected_participant} using {args.model}"
            )
            print("Type 'quit' to exit or use Ctrl+C")
            while True:
                try:
                    user_input = input("\nYou: ")
                    if user_input.lower() == "quit":
                        break

                    response = qa_chain.invoke(user_input)
                    print(f"\n{simulator.selected_participant}: {response}")

                except (KeyboardInterrupt, EOFError):
                    print("\nExiting...")
                    break
                except Exception as e:
                    print(f"\nError: {str(e)}")
                    print("Continuing...")

    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
