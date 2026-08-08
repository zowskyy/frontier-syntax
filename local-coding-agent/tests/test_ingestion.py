from pathlib import Path

import pytest

from local_agent.knowledge.ingestion import KnowledgeIngester, chunk_text
from local_agent.knowledge.store import KnowledgeStore


@pytest.fixture
def project_tree(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "module.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (root / "notes.md").write_text("# Notes\nProject documentation here.\n", encoding="utf-8")
    (root / "app.js").write_text("export function main() { return 42; }\n", encoding="utf-8")
    return root


def test_ingest_supported_files(project_tree):
    store = KnowledgeStore()
    ingester = KnowledgeIngester(store)
    project = store.create_project(str(project_tree), "project")

    results, errors = ingester.ingest_path(project.id, project_tree, project_tree)
    assert not errors
    assert len(results) == 3
    assert all(result.chunk_count >= 1 for result in results)


def test_duplicate_ingest_skipped(project_tree):
    store = KnowledgeStore()
    ingester = KnowledgeIngester(store)
    project = store.create_project(str(project_tree), "project")
    first = ingester.ingest_file(project.id, project_tree / "module.py", project_tree)
    second = ingester.ingest_file(project.id, project_tree / "module.py", project_tree)
    assert first.skipped_duplicate is False
    assert second.skipped_duplicate is True


def test_reingest_on_change(project_tree):
    store = KnowledgeStore()
    ingester = KnowledgeIngester(store)
    project = store.create_project(str(project_tree), "project")
    path = project_tree / "module.py"
    first = ingester.ingest_file(project.id, path, project_tree)
    path.write_text("def add(a, b):\n    return a + b + 1\n", encoding="utf-8")
    second = ingester.reingest_if_changed(project.id, path, project_tree)
    assert first.source_hash != second.source_hash


def test_chunker_overlap():
    text = "abcdefghijklmnopqrstuvwxyz" * 10
    chunks = chunk_text(text, chunk_size=50, overlap=10)
    assert len(chunks) > 1
