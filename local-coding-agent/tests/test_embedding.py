import pytest

from local_agent.knowledge.embedding import MockEmbeddingProvider


def test_mock_embedding_is_deterministic():
    provider = MockEmbeddingProvider(dimension=8)
    first = provider.embed("hello world")
    second = provider.embed("hello world")
    assert first.vector == second.vector
    assert first.model_id == provider.model_id
    assert first.dimension == 8


def test_mock_embedding_health_gate():
    provider = MockEmbeddingProvider(healthy=False)
    assert provider.health() is False
    with pytest.raises(RuntimeError):
        provider.embed("x")


def test_batch_embedding_respects_batch_size():
    provider = MockEmbeddingProvider(dimension=4)
    texts = ["a", "b", "c", "d", "e"]
    results = provider.embed_batch(texts, max_batch_size=2)
    assert len(results) == 5
