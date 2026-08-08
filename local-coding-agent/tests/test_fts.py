import pytest

from local_agent.knowledge.fts import FTSSearch
from local_agent.knowledge.store import KnowledgeStore, sha256_text


@pytest.fixture
def fts_store():
    store = KnowledgeStore()
    fts = FTSSearch(store)
    project = store.create_project("/tmp/search", "search")
    document = store.create_document(project.id, sha256_text("doc"), "1.0.0", "1.0.0")
    chunks = store.add_chunks(
        document.id,
        [
            (0, "def authenticate(user): pass", 4),
            (1, "class UserModel: pass", 3),
            (2, "README for project setup", 4),
        ],
    )
    for chunk in chunks:
        fts.index_chunk(chunk.id, chunk.text)
    yield store, fts
    store.close()


def test_search_finds_symbol(fts_store):
    _, fts = fts_store
    results = fts.search("authenticate")
    assert results
    assert "authenticate" in results[0].text


def test_phrase_search(fts_store):
    _, fts = fts_store
    results = fts.search("project setup", phrase=True)
    assert any("project setup" in result.text for result in results)


def test_parameterized_query_does_not_break_on_sql_chars(fts_store):
    _, fts = fts_store
    results = fts.search('"; DROP TABLE chunks; --')
    assert isinstance(results, list)


def test_rebuild_index_after_corruption(fts_store):
    store, fts = fts_store
    store.connection.execute("DROP TABLE chunks_fts")
    rebuilt = fts.recover_from_corruption()
    assert rebuilt >= 3
    results = fts.search("UserModel")
    assert results
