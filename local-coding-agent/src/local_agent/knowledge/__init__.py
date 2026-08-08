"""Knowledge layer — SQLite store, FTS5, embeddings, ingestion, retrieval."""

from local_agent.knowledge.embedding import EmbeddingProvider, MockEmbeddingProvider
from local_agent.knowledge.store import KnowledgeStore

__all__ = [
    "EmbeddingProvider",
    "KnowledgeStore",
    "MockEmbeddingProvider",
]
