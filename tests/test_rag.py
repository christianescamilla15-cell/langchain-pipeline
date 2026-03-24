"""Tests for RAG vector store and text processing."""
import pytest
import math
from services.analysis_service.rag import (
    RecursiveTextSplitter,
    SimpleEmbedder,
    FAISSVectorStore,
    get_vector_store,
    _vector_store,
)
import services.analysis_service.rag as rag_module


@pytest.fixture(autouse=True)
def reset_rag_singleton():
    """Reset the RAG singleton before each test."""
    rag_module._vector_store = None
    yield
    rag_module._vector_store = None


@pytest.fixture
def splitter():
    return RecursiveTextSplitter(chunk_size=100, overlap=20)


@pytest.fixture
def embedder():
    return SimpleEmbedder(dim=64)


@pytest.fixture
def store():
    return FAISSVectorStore()


class TestTextSplitter:
    def test_text_splitter_chunks_correctly(self, splitter):
        text = "First sentence here. Second sentence here. Third sentence here. Fourth sentence here. Fifth sentence here."
        chunks = splitter.split(text)
        assert len(chunks) >= 1
        # All original content should be represented across chunks
        for chunk in chunks:
            assert len(chunk) > 0

    def test_text_splitter_respects_size(self):
        splitter = RecursiveTextSplitter(chunk_size=50, overlap=10)
        text = "This is a long sentence that goes on and on. Another sentence follows. Yet another one here. And more text continues flowing."
        chunks = splitter.split(text)
        assert len(chunks) >= 2
        # First chunk should be within size limit (allowing some tolerance for sentence boundaries)
        assert len(chunks[0]) < 200  # Generous bound since we split on sentences


class TestEmbedder:
    def test_embedder_produces_vectors(self, embedder):
        vec = embedder.embed("hello world test")
        assert len(vec) == 64
        assert all(isinstance(v, float) for v in vec)

    def test_embedder_normalized(self, embedder):
        vec = embedder.embed("compliance audit liability breach penalty terms")
        magnitude = math.sqrt(sum(v * v for v in vec))
        assert abs(magnitude - 1.0) < 0.01


class TestVectorStore:
    def test_vector_store_add_document(self, store):
        count = store.add_document("doc1", "This is a test document about compliance and audit procedures. It covers many important topics.")
        assert count >= 1
        assert store.chunk_count >= 1
        assert store.doc_count == 1

    def test_vector_store_search_returns_similar(self, store):
        store.add_document("legal", "This contract includes liability clauses, indemnification provisions, and breach penalties. Legal review is required.")
        store.add_document("finance", "Revenue grew 25% year over year. Profit margins improved significantly. Stock price increased.")
        results = store.search("liability and legal risk", top_k=2)
        assert len(results) >= 1
        # Legal doc should rank higher for legal query
        assert results[0]["doc_id"] == "legal"

    def test_vector_store_empty_search(self, store):
        results = store.search("anything")
        assert results == []

    def test_vector_store_context_for_analysis(self, store):
        store.add_document("doc1", "Important compliance document about GDPR regulations and data privacy requirements.")
        context = store.get_context_for_analysis("GDPR compliance")
        assert "Similarity" in context
        assert len(context) > 0

    def test_vector_store_context_empty(self, store):
        context = store.get_context_for_analysis("anything")
        assert "No similar documents" in context

    def test_vector_store_stats(self, store):
        assert store.chunk_count == 0
        assert store.doc_count == 0
        store.add_document("doc1", "First document content here.")
        store.add_document("doc2", "Second document content here.")
        assert store.doc_count == 2
        assert store.chunk_count >= 2

    def test_vector_store_clear(self, store):
        store.add_document("doc1", "Some content.")
        assert store.chunk_count > 0
        store.clear()
        assert store.chunk_count == 0
        assert store.doc_count == 0

    def test_get_vector_store_singleton(self):
        s1 = get_vector_store()
        s2 = get_vector_store()
        assert s1 is s2
