"""RAG (Retrieval-Augmented Generation) with FAISS vector store.
Chunks documents, creates embeddings, and retrieves similar content."""

import re
import math
import json
import hashlib
from dataclasses import dataclass, field


@dataclass
class Chunk:
    text: str
    doc_id: str
    chunk_index: int
    embedding: list[float] = field(default_factory=list)


class SimpleEmbedder:
    """TF-IDF-like embedder for demo mode (no API needed)."""

    def __init__(self, dim: int = 128):
        self.dim = dim
        self._vocab: dict[str, int] = {}

    def embed(self, text: str) -> list[float]:
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        vec = [0.0] * self.dim
        for w in words:
            if w not in self._vocab:
                self._vocab[w] = int(hashlib.md5(w.encode()).hexdigest()[:8], 16) % self.dim
            vec[self._vocab[w]] += 1.0
        # Normalize
        magnitude = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / magnitude for v in vec]


class RecursiveTextSplitter:
    """Split text into chunks with overlap."""

    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def split(self, text: str) -> list[str]:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current = ""
        for sent in sentences:
            if len(current) + len(sent) > self.chunk_size and current:
                chunks.append(current.strip())
                # Keep overlap
                words = current.split()
                overlap_text = " ".join(words[-self.overlap // 5:]) if len(words) > self.overlap // 5 else ""
                current = overlap_text + " " + sent
            else:
                current += " " + sent
        if current.strip():
            chunks.append(current.strip())
        return chunks


class FAISSVectorStore:
    """In-memory FAISS-like vector store for document retrieval."""

    def __init__(self):
        self._chunks: list[Chunk] = []
        self._embedder = SimpleEmbedder()
        self._splitter = RecursiveTextSplitter()

    def add_document(self, doc_id: str, text: str) -> int:
        """Chunk, embed, and store a document. Returns chunk count."""
        raw_chunks = self._splitter.split(text)
        count = 0
        for i, chunk_text in enumerate(raw_chunks):
            embedding = self._embedder.embed(chunk_text)
            chunk = Chunk(text=chunk_text, doc_id=doc_id, chunk_index=i, embedding=embedding)
            self._chunks.append(chunk)
            count += 1
        return count

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        """Find most similar chunks to query."""
        if not self._chunks:
            return []
        query_emb = self._embedder.embed(query)
        scored = []
        for chunk in self._chunks:
            sim = self._cosine_similarity(query_emb, chunk.embedding)
            scored.append((sim, chunk))
        scored.sort(reverse=True, key=lambda x: x[0])
        return [
            {"text": c.text, "doc_id": c.doc_id, "chunk_index": c.chunk_index, "similarity": round(s, 4)}
            for s, c in scored[:top_k]
        ]

    def get_context_for_analysis(self, query: str, top_k: int = 3) -> str:
        """Get formatted context string for LLM prompts."""
        results = self.search(query, top_k)
        if not results:
            return "No similar documents found in the knowledge base."
        parts = []
        for r in results:
            parts.append(f"[Similarity: {r['similarity']:.2f}] {r['text'][:300]}")
        return "\n---\n".join(parts)

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = math.sqrt(sum(x * x for x in a)) or 1.0
        mag_b = math.sqrt(sum(x * x for x in b)) or 1.0
        return dot / (mag_a * mag_b)

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)

    @property
    def doc_count(self) -> int:
        return len(set(c.doc_id for c in self._chunks))

    def clear(self):
        self._chunks.clear()


# Singleton
_vector_store = None


def get_vector_store() -> FAISSVectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = FAISSVectorStore()
    return _vector_store
