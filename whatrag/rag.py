import argparse
import os
import signal
import sys
from typing import Iterator, List

from langchain_community.chat_loaders.whatsapp import WhatsAppChatLoader
from langchain_community.vectorstores import FAISS
from langchain_community.chat_loaders.utils import (
    map_ai_messages,
    merge_chat_runs,
)
from langchain_core.chat_sessions import ChatSession
from langchain_ollama import OllamaLLM
from langchain_ollama import OllamaEmbeddings
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from langchain.text_splitter import RecursiveCharacterTextSplitter

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

    def get_whatsapp_chat(self, chat_file: str) -> Iterator[ChatSession]:
        loader = WhatsAppChatLoader(chat_file)
        documents = loader.lazy_load()

        # Merge consecutive messages from the same sender into a single message
        merged_messages = merge_chat_runs(documents)
        return merged_messages

    def process_whatsapp_chat(self, chat_file: str):
        # Load and store the chat sessions once.
        self.chat_sessions = list(self.get_whatsapp_chat(chat_file))
        if not self.chat_sessions:
            print("Error: No chat sessions loaded from the chat file.")
            sys.exit(1)
        
        # Extract participants from the first chat session.
        # (Assuming the chat export contains one session. Adjust if necessary.)
        messages = self.chat_sessions[0]["messages"]
        for doc in messages:
            try:
                self.participants.add(doc.role)
            except AttributeError:
                # Skip invalid message formats
                pass

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

    def create_embeddings(self, messages: List[ChatSession], save_path: str):
        """Create and save embeddings for the chat messages."""
        # messages is expected to be a list of AIMessage objects.
        # Extract text from messages (assuming they have a .content attribute)
        texts = [msg.content for msg in messages[0]["messages"] if hasattr(msg, "content")]
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
        )
        
        docs = text_splitter.create_documents(texts)

        self.vector_store = FAISS.from_documents(docs, self.embeddings)
        self.vector_store.save_local(save_path)

    def load_embeddings(self, load_path: str):
        """Load existing embeddings from disk."""
        self.vector_store = FAISS.load_local(load_path, self.embeddings)

    def setup_qa_chain(self) -> RetrievalQA:
        """Set up the RAG chain for question answering."""
        prompt_template = f"""You are simulating {self.selected_participant} based on their WhatsApp messages.
Use the following chat history to understand their writing style, personality, and typical responses:

{{context}}

Based on the chat style above, respond to: {{question}}

Important: You are {self.selected_participant}. Maintain their typical message length, use of emojis, 
slang, and overall communication style as shown in the examples.
Response:"""

        PROMPT = PromptTemplate(
            template=prompt_template, input_variables=["context", "question"]
        )

        chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.vector_store.as_retriever(search_kwargs={"k": RETRIEVAL_K}),
            chain_type_kwargs={"prompt": PROMPT},
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
        "--chat-file", type=str, help="Path to WhatsApp chat export file"
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

    simulator = WhatsAppChatSimulator(model_name=args.model)

    try:
        # Create embeddings directory if it doesn't exist
        os.makedirs(args.embeddings_dir, exist_ok=True)

        # Process chat file if provided
        if args.chat_file:
            print(f"Processing chat file using {args.model}...")
            simulator.process_whatsapp_chat(args.chat_file)

            # Let user select which participant to simulate
            selected_participant = simulator.select_participant()
            print(f"\nSelected participant: {selected_participant}")

            # Instead of reloading the chat file, reuse the stored sessions.
            mapped_messages = list(
                map_ai_messages(simulator.chat_sessions, sender=selected_participant)
            )

            # Check if we got any messages
            if not mapped_messages:
                print("No messages found for the selected participant. Exiting...")
                sys.exit(1)

            # Create participant-specific embeddings path
            embeddings_path = os.path.join(
                args.embeddings_dir, f"faiss_store_{selected_participant}"
            )
            simulator.create_embeddings(mapped_messages, embeddings_path)
            print("Chat processing complete. Embeddings saved.")
        else:
            print("Error: Chat file is required for initial setup.")
            return

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

                    response = qa_chain.invoke({"query": user_input})
                    print(f"\n{simulator.selected_participant}: {response['result']}")

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
