import pytest

from local_agent.knowledge import chroma_adapter
from local_agent.knowledge.chroma_adapter import ChromaAdapter
from local_agent.knowledge.embedding import MockEmbeddingProvider


def test_fallback_when_chroma_missing(monkeypatch):
    monkeypatch.setattr(chroma_adapter, "CHROMADB_AVAILABLE", False)
    adapter = ChromaAdapter(MockEmbeddingProvider(), enabled=True)
    assert adapter.fallback_to_fts is True
    assert adapter.query("anything") == []


def test_collection_metadata_versioning():
    provider = MockEmbeddingProvider(model_id="mock/model:v1", dimension=8)
    adapter = ChromaAdapter(provider, enabled=False)
    assert adapter.available is False
    assert adapter.collection_metadata() is None


@pytest.mark.skipif(not chroma_adapter.CHROMADB_AVAILABLE, reason="chromadb not installed")
def test_rebuild_and_query_with_chroma(tmp_path):
    provider = MockEmbeddingProvider(dimension=8)
    adapter = ChromaAdapter(provider, persist_directory=str(tmp_path), enabled=True)
    count = adapter.rebuild(
        [
            ("chunk-1", "authenticate users safely", {"path": "auth.py"}),
            ("chunk-2", "database migration helpers", {"path": "db.py"}),
        ]
    )
    assert count == 2
    metadata = adapter.collection_metadata()
    assert metadata is not None
    assert metadata.embedding_model == provider.model_id
    results = adapter.query("authenticate")
    assert results
