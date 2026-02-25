import os
import re
import hashlib
from typing import Any, cast

try:
    from langchain_community.vectorstores import FAISS as LangchainFAISS
    from langchain_ollama import OllamaEmbeddings as LangchainOllamaEmbeddings
except Exception:
    LangchainFAISS = None
    LangchainOllamaEmbeddings = None


def get_int_env(name: str, default: int, min_value: int = 1) -> int:
    """Read an integer environment variable with safe fallback and lower bound."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(value, min_value)


def clamp_text(text: str, max_chars: int) -> str:
    """Normalize whitespace and clamp long messages for prompt/index efficiency."""
    cleaned = re.sub(r"\s+", " ", text.strip())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 1].rstrip() + "…"


class EmbeddingRAG:
    """Embedding-based retrieval over WhatsApp chat messages with FAISS cache reuse."""

    def __init__(self, max_message_chars: int):
        """Initialize retrieval settings from env and configure cache paths."""
        self.max_message_chars = max_message_chars
        self.embed_model = os.environ.get("RAG_EMBED_MODEL", "qwen3-embedding:4b").strip() or "qwen3-embedding:4b"
        self.retrieval_count = get_int_env("RAG_RETRIEVAL_COUNT", 32)
        self.vector_search_k = get_int_env("RAG_VECTOR_SEARCH_K", 48)
        self.neighbor_radius = get_int_env("RAG_CONTEXT_NEIGHBOR_RADIUS", 1, min_value=0)
        self.cache_dir = os.environ.get(
            "RAG_VECTOR_CACHE_DIR",
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".cache", "faiss"),
        ).strip()
        self._embeddings_model: Any = None

    def _get_embeddings_model(self) -> Any:
        """Lazily initialize and cache the Ollama embedding model instance."""
        if self._embeddings_model is not None:
            return self._embeddings_model
        if LangchainOllamaEmbeddings is None:
            return None
        try:
            self._embeddings_model = LangchainOllamaEmbeddings(model=self.embed_model)
            return self._embeddings_model
        except Exception:
            return None

    def _get_vector_cache_path(self, snapshot: dict[str, Any]) -> str:
        """Build a stable cache key from chat file identity + model for FAISS reuse."""
        fpath = str(snapshot.get("fpath", ""))
        mtime = str(snapshot.get("mtime", ""))
        responder = str(snapshot.get("responder_name", ""))
        key_raw = f"{fpath}|{mtime}|{responder}|{self.embed_model}"
        key = hashlib.sha1(key_raw.encode("utf-8")).hexdigest()[:24]
        return os.path.join(self.cache_dir, key)

    def _load_vector_store(self, cache_path: str, embeddings: Any) -> Any:
        """Load a previously saved FAISS index from disk cache."""
        faiss_cls = cast(Any, LangchainFAISS)
        try:
            return faiss_cls.load_local(
                cache_path,
                embeddings,
                allow_dangerous_deserialization=True,
            )
        except TypeError:
            return faiss_cls.load_local(cache_path, embeddings)

    def _save_vector_store(self, vector_store: Any, cache_path: str) -> None:
        """Persist FAISS index to disk for cross-process reuse."""
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        vector_store.save_local(cache_path)

    def ensure_vector_store(self, snapshot: dict[str, Any]) -> None:
        """Ensure snapshot has a ready vector store, loading cache or building as needed."""
        if snapshot.get("vector_ready"):
            return
        if LangchainFAISS is None:
            raise RuntimeError("FAISS is unavailable. Install langchain-community/faiss dependencies.")

        embeddings = self._get_embeddings_model()
        if embeddings is None:
            raise RuntimeError(
                f"Embedding model unavailable: '{self.embed_model}'. Ensure Ollama is running and model is pulled."
            )

        cache_path = self._get_vector_cache_path(snapshot)
        if os.path.isdir(cache_path):
            try:
                snapshot["vector_store"] = self._load_vector_store(cache_path, embeddings)
                snapshot["vector_ready"] = True
                return
            except Exception:
                pass

        parsed: list[tuple[str, str]] = snapshot["parsed"]
        texts: list[str] = []
        metadatas: list[dict[str, Any]] = []
        for idx, (sender, text) in enumerate(parsed):
            cleaned = clamp_text(text, self.max_message_chars)
            if not cleaned:
                continue
            texts.append(f"[{sender}]: {cleaned}")
            metadatas.append({"idx": idx, "sender": sender})

        if not texts:
            raise RuntimeError("No chat text available to index for embeddings retrieval.")

        try:
            faiss_cls = cast(Any, LangchainFAISS)
            vector_store = faiss_cls.from_texts(texts=texts, embedding=embeddings, metadatas=metadatas)
            self._save_vector_store(vector_store, cache_path)
            snapshot["vector_store"] = vector_store
            snapshot["vector_ready"] = True
        except Exception as e:
            raise RuntimeError(f"Failed to build vector index: {e}") from e

    def relevant_history(self, snapshot: dict[str, Any], user_message: str, limit: int | None = None) -> list[tuple[str, str]]:
        """Retrieve relevant chat lines for a user message using semantic search + neighbor expansion."""
        limit = limit or self.retrieval_count
        self.ensure_vector_store(snapshot)
        vector_store = snapshot.get("vector_store")
        if vector_store is None:
            raise RuntimeError("Vector store is not initialized.")

        try:
            docs = vector_store.similarity_search(user_message, k=self.vector_search_k)
        except Exception as e:
            raise RuntimeError(f"Vector similarity search failed: {e}") from e

        parsed: list[tuple[str, str]] = snapshot["parsed"]
        seen: set[tuple[str, str]] = set()
        seen_indices: set[int] = set()
        ranked_indices: list[int] = []

        for doc in docs:
            metadata = cast(dict[str, Any], doc.metadata or {})
            idx = int(metadata.get("idx", -1))
            if idx < 0 or idx >= len(parsed):
                continue
            if idx in seen_indices:
                continue
            seen_indices.add(idx)
            ranked_indices.append(idx)

        if not ranked_indices:
            return []

        expanded_indices: list[int] = []
        expanded_seen: set[int] = set()
        for idx in ranked_indices:
            left = max(0, idx - self.neighbor_radius)
            right = min(len(parsed) - 1, idx + self.neighbor_radius)
            for neighbor_idx in range(left, right + 1):
                if neighbor_idx in expanded_seen:
                    continue
                expanded_seen.add(neighbor_idx)
                expanded_indices.append(neighbor_idx)

        results: list[tuple[str, str]] = []
        for idx in expanded_indices:
            sender, text = parsed[idx]
            cleaned = clamp_text(text, self.max_message_chars)
            if not sender or not cleaned:
                continue
            key = (sender, cleaned)
            if key in seen:
                continue
            seen.add(key)
            results.append(key)
            if len(results) >= limit:
                break

        return results
