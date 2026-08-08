import pytest

from local_agent.knowledge.store import KnowledgeStore, sha256_text


@pytest.fixture
def store():
    with KnowledgeStore() as knowledge_store:
        yield knowledge_store


def test_create_project_and_file(store):
    project = store.create_project("/tmp/demo", "demo")
    file_record = store.upsert_file(project.id, "README.md", sha256_text("hello"))
    assert file_record.project_id == project.id
    assert file_record.relative_path == "README.md"


def test_document_deduplication_by_source_hash(store):
    project = store.create_project("/tmp/demo", "demo")
    source_hash = sha256_text("same-content")
    first = store.create_document(project.id, source_hash, "1.0.0", "1.0.0")
    found = store.find_document_by_source_hash(project.id, source_hash)
    assert found is not None
    assert found.id == first.id


def test_chunks_persist_with_order(store):
    project = store.create_project("/tmp/demo", "demo")
    document = store.create_document(project.id, sha256_text("doc"), "1.0.0", "1.0.0")
    store.add_chunks(
        document.id,
        [(0, "alpha", 1), (1, "beta", 1)],
    )
    chunks = store.list_chunks(document.id)
    assert [chunk.text for chunk in chunks] == ["alpha", "beta"]


def test_schema_migration_recorded(store):
    row = store.connection.execute("SELECT version FROM schema_migrations").fetchone()
    assert row["version"] >= 1
