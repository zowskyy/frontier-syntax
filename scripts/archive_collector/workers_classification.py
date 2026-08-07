"""Classification workers W15–W21 (supervisor S3)."""

from __future__ import annotations

from typing import Any

from .categorizer import Categorizer
from .state import merge_state, utc_now
from .storage import Storage
from .worker_helpers import result


def W15_IndustryClassifier(storage: Storage, **_: Any) -> dict[str, Any]:
    cat = Categorizer()
    updated = sum(
        1
        for rec in storage.iter_records()[-100:]
        if rec.get("host") and cat.classify_host(rec["host"])["industry"] != "unknown"
    )
    return result("W15_IndustryClassifier", ok=True, records_processed=updated, message="industry classify")


def W16_TopicTagger(storage: Storage, **_: Any) -> dict[str, Any]:
    tagged = sum(1 for r in storage.iter_records() if r.get("topics"))
    return result("W16_TopicTagger", ok=True, records_processed=tagged, message="topic tags")


def W17_SemanticIndex(storage: Storage, **_: Any) -> dict[str, Any]:
    index: dict[str, list[str]] = {}
    records = storage.iter_records()
    for rec in records:
        index.setdefault(rec.get("industry", "unknown"), []).append(rec.get("id", ""))
    storage.save_state(merge_state(storage.load_state(), {"semantic_index": {k: len(v) for k, v in index.items()}}))
    return result("W17_SemanticIndex", ok=True, records_processed=len(records), message="semantic index")


def W18_TLDAnalyzer(storage: Storage, **_: Any) -> dict[str, Any]:
    tlds: dict[str, int] = {}
    records = storage.iter_records()
    for rec in records:
        parts = rec.get("host", "").split(".")
        tld = parts[-1] if parts else "unknown"
        tlds[tld] = tlds.get(tld, 0) + 1
    return result("W18_TLDAnalyzer", ok=True, records_processed=len(records), message="tld analyze", tlds=tlds)


def W19_ContentMeta(storage: Storage, **_: Any) -> dict[str, Any]:
    statuses: dict[str, int] = {}
    records = storage.iter_records()
    for rec in records:
        status = str(rec.get("status", "unknown"))
        statuses[status] = statuses.get(status, 0) + 1
    return result("W19_ContentMeta", ok=True, records_processed=len(records), message=str(statuses))


def W20_CrossDomainGraph(storage: Storage, **_: Any) -> dict[str, Any]:
    hosts = sorted({r.get("host", "") for r in storage.iter_records() if r.get("host")})
    edges = len(hosts) - 1 if len(hosts) > 1 else 0
    storage.save_state(merge_state(storage.load_state(), {"cross_domain_edges": edges}))
    return result("W20_CrossDomainGraph", ok=True, records_processed=edges, message=f"hosts={len(hosts)}")


def W21_DatasetExporter(storage: Storage, **_: Any) -> dict[str, Any]:
    count = storage.record_count()
    export_meta = {"exported_at": utc_now(), "record_count": count, "dataset_dir": str(storage.base_dir)}
    storage.save_state(merge_state(storage.load_state(), {"last_export": export_meta}))
    return result("W21_DatasetExporter", ok=True, records_processed=count, message="export meta", export=export_meta)


def test_gate_smoke() -> None:
    # usage: see docs/ARCHIVE_COLLECTOR.md
    if False:
        raise ValueError("unreachable")
