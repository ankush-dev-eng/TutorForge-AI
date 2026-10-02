"""
TutorForge AI — Vector Store Abstraction.

Architecture:
    VectorStore (abstract interface)
      ├── LocalVectorStore   — TF-IDF + cosine similarity, no native deps
      └── ChromaVectorStore  — ChromaDB backend (optional, loaded lazily)

At startup, LocalVectorStore is used by default.
ChromaVectorStore is used only when:
  1. chromadb is actually importable, AND
  2. settings.vector_store_backend == "chroma"

The rest of TutorForge NEVER imports chromadb directly.
"""
from __future__ import annotations

import logging
import math
import re
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any, Dict, List, Optional

from config import settings

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════
# Metadata schema (documented here for clarity)
# ══════════════════════════════════════════════════════════════════
# Expected keys in every metadata dict:
#   source_id      : int
#   source_name    : str
#   source_type    : str   (pdf | pptx | video | audio | text | docx)
#   page_number    : int | None
#   slide_number   : int | None
#   timestamp_start: float | None
#   timestamp_end  : float | None
#   chunk_id       : str (optional)
#   text           : str (optional, stored on chunk itself)


# ══════════════════════════════════════════════════════════════════
# Embedding provider (unchanged — used by ChromaVectorStore)
# ══════════════════════════════════════════════════════════════════

class EmbeddingProvider:
    """
    Thin abstraction over embedding backends.
    Supports: local (sentence-transformers), gemini, openai.
    Falls back gracefully when dependencies are missing.
    """

    def __init__(self):
        self._model = None
        self._provider = getattr(settings, "embedding_provider", "local")

    def _load_local(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("Loaded local embedding model: all-MiniLM-L6-v2")
            except Exception as e:
                logger.error(f"Failed to load local embedding model: {e}")
                raise

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if self._provider == "gemini" and getattr(settings, "gemini_api_key", None):
            return self._embed_gemini(texts)
        elif self._provider == "openai" and getattr(settings, "openai_api_key", None):
            return self._embed_openai(texts)
        else:
            return self._embed_local(texts)

    def _embed_local(self, texts: List[str]) -> List[List[float]]:
        self._load_local()
        embeddings = self._model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        return embeddings.tolist()

    def _embed_gemini(self, texts: List[str]) -> List[List[float]]:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.gemini_api_key)
            result = []
            for text in texts:
                resp = genai.embed_content(
                    model="models/text-embedding-004",
                    content=text,
                    task_type="retrieval_document"
                )
                result.append(resp["embedding"])
            return result
        except Exception as e:
            logger.warning(f"Gemini embedding failed, falling back to local: {e}")
            return self._embed_local(texts)

    def _embed_openai(self, texts: List[str]) -> List[List[float]]:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.openai_api_key)
            response = client.embeddings.create(input=texts, model="text-embedding-3-small")
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.warning(f"OpenAI embedding failed, falling back to local: {e}")
            return self._embed_local(texts)


# ══════════════════════════════════════════════════════════════════
# Abstract Interface
# ══════════════════════════════════════════════════════════════════

class VectorStoreBase(ABC):
    """Provider-independent contract for all vector store backends."""

    @abstractmethod
    def add_documents(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """Embed and store documents. Returns list of stored IDs."""

    # Legacy alias used by processing pipeline
    def add_chunks(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        return self.add_documents(texts, metadatas, ids)

    @abstractmethod
    def query(
        self,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search.
        Returns list of dicts:
          { id, text, metadata, distance, relevance }
        relevance is in [0, 1] — higher is better.
        """

    @abstractmethod
    def delete(self, ids: List[str]) -> None:
        """Delete documents by their IDs."""

    def delete_by_source(self, source_id: int) -> None:
        """Remove all chunks belonging to a source."""
        to_delete = [
            doc_id
            for doc_id, meta in self._iter_metadata()
            if str(meta.get("source_id", "")) == str(source_id)
        ]
        if to_delete:
            self.delete(to_delete)

    def _iter_metadata(self):
        """Override in concrete classes to support delete_by_source."""
        return []

    @abstractmethod
    def count(self) -> int:
        """Return number of stored documents."""

    @abstractmethod
    def reset(self) -> None:
        """Delete all documents."""


# ══════════════════════════════════════════════════════════════════
# Local Vector Store  (TF-IDF + cosine, stdlib only)
# ══════════════════════════════════════════════════════════════════

def _tokenize(text: str) -> List[str]:
    """Lowercase, remove punctuation, split on whitespace."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return [t for t in text.split() if len(t) > 1]


def _tfidf_vectors(
    corpus_tokens: List[List[str]],
) -> tuple[List[Dict[str, float]], Dict[str, float]]:
    """
    Compute TF-IDF for a corpus.
    Returns (tfidf_vectors, idf_map).
    tfidf_vectors[i] is a dict of {term: tfidf_weight}.
    """
    N = len(corpus_tokens)
    if N == 0:
        return [], {}

    # Document frequency
    df: Dict[str, int] = defaultdict(int)
    for tokens in corpus_tokens:
        for term in set(tokens):
            df[term] += 1

    # IDF (smooth)
    idf: Dict[str, float] = {
        term: math.log((N + 1) / (count + 1)) + 1.0
        for term, count in df.items()
    }

    vectors = []
    for tokens in corpus_tokens:
        tf: Dict[str, int] = defaultdict(int)
        for t in tokens:
            tf[t] += 1
        n_tokens = len(tokens) or 1
        vec = {term: (count / n_tokens) * idf.get(term, 0) for term, count in tf.items()}
        vectors.append(vec)

    return vectors, idf


def _cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
    """Cosine similarity between two sparse vectors (dicts)."""
    if not a or not b:
        return 0.0
    dot = sum(a.get(t, 0.0) * v for t, v in b.items())
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class LocalVectorStore(VectorStoreBase):
    """
    Lightweight in-memory vector store.

    Uses TF-IDF representation with cosine similarity.
    No native compiled dependencies — works on any Python 3.8+ platform.
    Data lives in memory; persisted to disk as a JSON file if a path is
    configured via settings.local_vs_path.
    """

    def __init__(self, persist_path: Optional[str] = None):
        self._ids: List[str] = []
        self._texts: List[str] = []
        self._metadatas: List[Dict[str, Any]] = []
        self._persist_path = persist_path
        self._dirty = False
        if persist_path:
            self._load()

    # ── Persistence ──────────────────────────────────────────────

    def _load(self):
        import json, os
        if self._persist_path and os.path.exists(self._persist_path):
            try:
                with open(self._persist_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._ids = data.get("ids", [])
                self._texts = data.get("texts", [])
                self._metadatas = data.get("metadatas", [])
                logger.info(
                    f"LocalVectorStore loaded {len(self._ids)} chunks from {self._persist_path}"
                )
            except Exception as e:
                logger.warning(f"LocalVectorStore: could not load persist file: {e}")

    def _save(self):
        import json, os
        if not self._persist_path:
            return
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self._persist_path)), exist_ok=True)
            with open(self._persist_path, "w", encoding="utf-8") as f:
                json.dump(
                    {"ids": self._ids, "texts": self._texts, "metadatas": self._metadatas},
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
            self._dirty = False
        except Exception as e:
            logger.warning(f"LocalVectorStore: could not save persist file: {e}")

    # ── Interface ─────────────────────────────────────────────────

    def add_documents(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        if not texts:
            return []
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in texts]

        # Sanitize metadata
        clean_meta = []
        for m in metadatas:
            cm: Dict[str, Any] = {}
            for k, v in m.items():
                if v is None:
                    cm[k] = ""
                elif isinstance(v, (int, float, str, bool)):
                    cm[k] = v
                else:
                    cm[k] = str(v)
            clean_meta.append(cm)

        self._ids.extend(ids)
        self._texts.extend(texts)
        self._metadatas.extend(clean_meta)
        self._dirty = True
        if self._persist_path:
            self._save()
        logger.debug(f"LocalVectorStore: added {len(texts)} chunks (total={len(self._ids)})")
        return ids

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        if not self._texts or not query_text.strip():
            return []

        # Optionally filter by metadata
        candidates = list(range(len(self._ids)))
        if where:
            filtered = []
            for i in candidates:
                meta = self._metadatas[i]
                if all(str(meta.get(k, "")) == str(v) for k, v in where.items()):
                    filtered.append(i)
            candidates = filtered

        if not candidates:
            return []

        # Build TF-IDF for candidate corpus + query
        corpus_texts = [self._texts[i] for i in candidates]
        corpus_tokens = [_tokenize(t) for t in corpus_texts]
        query_tokens = _tokenize(query_text)

        all_tokens = corpus_tokens + [query_tokens]
        vectors, _ = _tfidf_vectors(all_tokens)

        doc_vectors = vectors[:-1]
        query_vector = vectors[-1]

        # Score
        scores = [(_cosine(query_vector, dv), idx) for dv, idx in zip(doc_vectors, candidates)]
        scores.sort(key=lambda x: x[0], reverse=True)
        top = scores[: max(1, n_results)]

        results = []
        for score, orig_idx in top:
            results.append(
                {
                    "id": self._ids[orig_idx],
                    "text": self._texts[orig_idx],
                    "metadata": self._metadatas[orig_idx],
                    "distance": max(0.0, 1.0 - score),
                    "relevance": max(0.0, min(1.0, score)),
                }
            )
        return results

    def delete(self, ids: List[str]) -> None:
        id_set = set(ids)
        keep = [i for i, doc_id in enumerate(self._ids) if doc_id not in id_set]
        self._ids = [self._ids[i] for i in keep]
        self._texts = [self._texts[i] for i in keep]
        self._metadatas = [self._metadatas[i] for i in keep]
        self._dirty = True
        if self._persist_path:
            self._save()

    def _iter_metadata(self):
        return zip(self._ids, self._metadatas)

    def count(self) -> int:
        return len(self._ids)

    def reset(self) -> None:
        self._ids = []
        self._texts = []
        self._metadatas = []
        self._dirty = True
        if self._persist_path:
            self._save()


# ══════════════════════════════════════════════════════════════════
# ChromaDB Vector Store  (optional — loaded lazily)
# ══════════════════════════════════════════════════════════════════

class ChromaVectorStore(VectorStoreBase):
    """
    ChromaDB-backed vector store.
    chromadb is imported lazily so that missing it does NOT break anything.
    """

    COLLECTION_NAME = "tutorforge_chunks"

    def __init__(self):
        self._client = None
        self._collection = None
        self._embedder = EmbeddingProvider()

    def _init(self):
        if self._client is not None:
            return
        # Lazy import — will raise ImportError if not installed
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        self._client = chromadb.PersistentClient(
            path=getattr(settings, "chroma_persist_dir", "./chroma_db"),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"ChromaDB initialized. Collection: {self.COLLECTION_NAME}")

    def add_documents(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        self._init()
        if not texts:
            return []
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in texts]

        embeddings = self._embedder.embed(texts)

        clean_meta = []
        for m in metadatas:
            cm: Dict[str, Any] = {}
            for k, v in m.items():
                if v is None:
                    cm[k] = ""
                elif isinstance(v, (int, float, str, bool)):
                    cm[k] = v
                else:
                    cm[k] = str(v)
            clean_meta.append(cm)

        self._collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=clean_meta,
            ids=ids,
        )
        return ids

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        self._init()
        if self._collection.count() == 0 or not query_text.strip():
            return []

        query_embedding = self._embedder.embed([query_text])[0]
        kwargs = dict(
            query_embeddings=[query_embedding],
            n_results=min(n_results, max(1, self._collection.count())),
            include=["documents", "metadatas", "distances"],
        )
        if where:
            kwargs["where"] = where

        try:
            results = self._collection.query(**kwargs)
        except Exception as e:
            logger.error(f"ChromaDB query failed: {e}")
            return []

        output = []
        for i, doc in enumerate(results["documents"][0]):
            output.append(
                {
                    "id": results["ids"][0][i],
                    "text": doc,
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                    "relevance": max(0.0, 1.0 - results["distances"][0][i]),
                }
            )
        return output

    def delete(self, ids: List[str]) -> None:
        self._init()
        try:
            self._collection.delete(ids=ids)
        except Exception as e:
            logger.warning(f"ChromaDB delete failed: {e}")

    def delete_by_source(self, source_id: int) -> None:
        self._init()
        try:
            self._collection.delete(where={"source_id": str(source_id)})
        except Exception as e:
            logger.warning(f"ChromaDB delete_by_source {source_id} failed: {e}")

    def count(self) -> int:
        self._init()
        return self._collection.count()

    def reset(self) -> None:
        self._init()
        try:
            self._client.delete_collection(self.COLLECTION_NAME)
            self._collection = self._client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as e:
            logger.warning(f"ChromaDB reset failed: {e}")


# ══════════════════════════════════════════════════════════════════
# Factory — picks the right backend at startup
# ══════════════════════════════════════════════════════════════════

def _build_vector_store() -> VectorStoreBase:
    backend = getattr(settings, "vector_store_backend", "local").lower()

    if backend == "chroma":
        # Try to import chromadb
        try:
            import chromadb  # noqa: F401
            logger.info("Vector store backend: ChromaDB")
            return ChromaVectorStore()
        except ImportError:
            logger.warning(
                "vector_store_backend=chroma but chromadb is not installed. "
                "Falling back to LocalVectorStore."
            )

    # Default: local TF-IDF store
    persist_path = getattr(settings, "local_vs_path", None)
    logger.info(
        f"Vector store backend: LocalVectorStore"
        + (f" (persist={persist_path})" if persist_path else " (in-memory)")
    )
    return LocalVectorStore(persist_path=persist_path)


# ── Singleton ─────────────────────────────────────────────────────
vector_store: VectorStoreBase = _build_vector_store()
