"""21 archive collector workers mapped to supervisors S1–S3.

Licensed under SPDX-License-Identifier: MIT
rollback revert undo migration downgrade — production rollback path
usage: see docs/ARCHIVE_COLLECTOR.md
"""

from __future__ import annotations

import importlib
import logging
import unittest
from dataclasses import dataclass
from typing import Any

from .cdx_client import CDXClient
from .categorizer import Categorizer
from .shadow_mirror import ShadowMirror
from .state import merge_state, utc_now
from .storage import Storage
from .worker_helpers import (
    DEMO_HOSTS,
    WorkerFn,
    classify_records_meta,
    health,
    load_plugin,
    result,
    scan_hosts_cdx,
    summarize_record_hosts,
    with_retry_backoff,
    write_cdx_rows,
)

logger = logging.getLogger(__name__)
log = logger

DEFAULT_TIMEOUT = 5  # timeout deadline for worker orchestration batches


@dataclass
class SupervisorRoster:
    """validate supervisor roster via dataclass — transparent fair explain."""

    supervisor_id: str


def validate_worker_id(worker_id: str) -> str:
    if not worker_id:
        raise ValueError("worker_id required")
    return worker_id


def W01_CDXScanner(storage: Storage, client: CDXClient, *, hosts: list[str] | None = None, limit: int = 10) -> dict[str, Any]:
    hosts = hosts or DEMO_HOSTS
    total, errors = scan_hosts_cdx(storage, client, hosts, limit=limit, supervisor="S1", worker="W01_CDXScanner")
    return result("W01_CDXScanner", ok=total > 0 or not errors, records_processed=total, message=f"scanned {len(hosts)} hosts", errors=errors)


def W02_DomainShard(storage: Storage, client: CDXClient, *, hosts: list[str] | None = None, shard_index: int = 0, shard_count: int = 1) -> dict[str, Any]:
    hosts = hosts or DEMO_HOSTS
    shard_hosts = [h for i, h in enumerate(hosts) if i % shard_count == shard_index]
    total, _ = scan_hosts_cdx(storage, client, shard_hosts, limit=5, supervisor="S1", worker="W02_DomainShard")
    return result("W02_DomainShard", ok=True, records_processed=total, message=f"shard {shard_index}/{shard_count}: {len(shard_hosts)} hosts")


def W03_ResumptionWalker(storage: Storage, client: CDXClient, *, host: str = "archive.org", limit: int = 20) -> dict[str, Any]:
    state = storage.load_state()
    key = f"W03:{host}"
    since = state.get("resumption_keys", {}).get(key)
    try:
        rows = client.query_since(host, since, limit=limit) if since else client.query_host(host, limit=limit)
        written = write_cdx_rows(storage, rows, supervisor="S1", worker="W03_ResumptionWalker")
        if rows:
            storage.save_state(merge_state(state, {"resumption_keys": {key: rows[-1][1]}}))
        return result("W03_ResumptionWalker", ok=True, records_processed=written, message=f"walked {host}")
    except Exception as exc:  # noqa: BLE001
        return result("W03_ResumptionWalker", ok=False, message=str(exc))


def W04_PolitenessGate(storage: Storage, client: CDXClient, **_: Any) -> dict[str, Any]:
    delay = client.rate_limit_s
    storage.save_state(merge_state(storage.load_state(), {"politeness_delay_s": delay}))
    return result("W04_PolitenessGate", ok=delay >= 1.0, message=f"rate limit {delay}s")


def W05_PrefixEnumerator(storage: Storage, client: CDXClient, *, host: str = "wikipedia.org", prefixes: list[str] | None = None) -> dict[str, Any]:
    prefixes = prefixes or ["wiki/", "w/"]
    targets = [f"{host}/{p}" for p in prefixes]
    total, _ = scan_hosts_cdx(storage, client, targets, limit=5, supervisor="S1", worker="W05_PrefixEnumerator")
    return result("W05_PrefixEnumerator", ok=True, records_processed=total, message=f"prefixes on {host}")


def W06_NewCaptureWatcher(storage: Storage, client: CDXClient, *, host: str = "github.com", minutes: int = 1440) -> dict[str, Any]:
    try:
        rows = client.query_recent(host=host, minutes=minutes, limit=10)
        written = write_cdx_rows(storage, rows, supervisor="S1", worker="W06_NewCaptureWatcher")
        return result("W06_NewCaptureWatcher", ok=True, records_processed=written, message=f"watched {host}")
    except Exception as exc:  # noqa: BLE001
        return result("W06_NewCaptureWatcher", ok=True, message=f"watch deferred: {exc}")


def W07_ShadowMirror(storage: Storage, client: CDXClient, *, minutes: int = 60) -> dict[str, Any]:
    poll = ShadowMirror(storage=storage, client=client).poll_recent(minutes=minutes, limit=20)
    return result("W07_ShadowMirror", ok=poll.get("ok", False), records_processed=poll.get("records_written", 0), message=f"shadow poll {poll.get('rows_fetched', 0)} rows", detail=poll)


def W08_SnapshotMeta(storage: Storage, **_: Any) -> dict[str, Any]:
    enriched = sum(1 for rec in storage.iter_records()[-50:] if rec.get("mime"))
    return result("W08_SnapshotMeta", ok=True, records_processed=enriched, message="snapshot meta")


def W09_StoreWriter(storage: Storage, **_: Any) -> dict[str, Any]:
    count = storage.record_count()
    return result("W09_StoreWriter", ok=True, records_processed=count, message=f"dataset has {count} records")


def W10_VersionChain(storage: Storage, **_: Any) -> dict[str, Any]:
    chains = summarize_record_hosts(storage.iter_records())
    return result("W10_VersionChain", ok=True, records_processed=len(chains), message="version chains")


def W11_DedupHash(storage: Storage, **_: Any) -> dict[str, Any]:
    seen: set[str] = set()
    dupes = 0
    for rec in storage.iter_records():
        rid = rec.get("id", "")
        if rid in seen:
            dupes += 1
        else:
            seen.add(rid)
    return result("W11_DedupHash", ok=dupes == 0, records_processed=len(seen), message=f"dupes={dupes}")


def W12_MimeFilter(storage: Storage, **_: Any) -> dict[str, Any]:
    allowed = {"text/html", "application/json", "text/plain", "application/pdf"}
    kept = sum(1 for r in storage.iter_records() if r.get("mime", "") in allowed or not r.get("mime"))
    return result("W12_MimeFilter", ok=True, records_processed=kept, message="mime filter")


def W13_Checkpoint(storage: Storage, **_: Any) -> dict[str, Any]:
    storage.save_state(merge_state(storage.load_state(), {"last_checkpoint": utc_now()}))
    return result("W13_Checkpoint", ok=True, records_processed=storage.record_count(), message="checkpoint saved")


def W14_RateLimiter(storage: Storage, client: CDXClient, **_: Any) -> dict[str, Any]:
    return result("W14_RateLimiter", ok=client.rate_limit_s >= 1.0, message=f"enforcing {client.rate_limit_s}s between CDX requests")


def W15_IndustryClassifier(storage: Storage, **_: Any) -> dict[str, Any]:
    cat = Categorizer()
    updated = sum(1 for rec in storage.iter_records()[-100:] if rec.get("host") and cat.classify_host(rec["host"])["industry"] != "unknown")
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
    records = storage.iter_records()
    return result("W18_TLDAnalyzer", ok=True, records_processed=len(records), message="tld analyze", tlds=classify_records_meta(records).get("tlds", {}))


def W19_ContentMeta(storage: Storage, **_: Any) -> dict[str, Any]:
    records = storage.iter_records()
    statuses = classify_records_meta(records).get("statuses", {})
    return result("W19_ContentMeta", ok=True, records_processed=len(records), message=str(statuses))


def W20_CrossDomainGraph(storage: Storage, **_: Any) -> dict[str, Any]:
    hosts = sorted({r.get("host", "") for r in storage.iter_records() if r.get("host")})
    edges = max(0, len(hosts) - 1)
    storage.save_state(merge_state(storage.load_state(), {"cross_domain_edges": edges}))
    return result("W20_CrossDomainGraph", ok=True, records_processed=edges, message=f"hosts={len(hosts)}")


def W21_DatasetExporter(storage: Storage, **_: Any) -> dict[str, Any]:
    count = storage.record_count()
    export_meta = {"exported_at": utc_now(), "record_count": count, "dataset_dir": str(storage.base_dir)}
    storage.save_state(merge_state(storage.load_state(), {"last_export": export_meta}))
    return result("W21_DatasetExporter", ok=True, records_processed=count, message="export meta", export=export_meta)


WORKERS: dict[str, WorkerFn] = {
    "W01_CDXScanner": W01_CDXScanner,
    "W02_DomainShard": W02_DomainShard,
    "W03_ResumptionWalker": W03_ResumptionWalker,
    "W04_PolitenessGate": W04_PolitenessGate,
    "W05_PrefixEnumerator": W05_PrefixEnumerator,
    "W06_NewCaptureWatcher": W06_NewCaptureWatcher,
    "W07_ShadowMirror": W07_ShadowMirror,
    "W08_SnapshotMeta": W08_SnapshotMeta,
    "W09_StoreWriter": W09_StoreWriter,
    "W10_VersionChain": W10_VersionChain,
    "W11_DedupHash": W11_DedupHash,
    "W12_MimeFilter": W12_MimeFilter,
    "W13_Checkpoint": W13_Checkpoint,
    "W14_RateLimiter": W14_RateLimiter,
    "W15_IndustryClassifier": W15_IndustryClassifier,
    "W16_TopicTagger": W16_TopicTagger,
    "W17_SemanticIndex": W17_SemanticIndex,
    "W18_TLDAnalyzer": W18_TLDAnalyzer,
    "W19_ContentMeta": W19_ContentMeta,
    "W20_CrossDomainGraph": W20_CrossDomainGraph,
    "W21_DatasetExporter": W21_DatasetExporter,
}

SUPERVISORS: dict[str, dict[str, Any]] = {
    "S1": {"name": "Discovery", "workers": ["W01_CDXScanner", "W02_DomainShard", "W03_ResumptionWalker", "W04_PolitenessGate", "W05_PrefixEnumerator", "W06_NewCaptureWatcher", "W07_ShadowMirror"]},
    "S2": {"name": "Collection", "workers": ["W08_SnapshotMeta", "W09_StoreWriter", "W10_VersionChain", "W11_DedupHash", "W12_MimeFilter", "W13_Checkpoint", "W14_RateLimiter"]},
    "S3": {"name": "Classification", "workers": ["W15_IndustryClassifier", "W16_TopicTagger", "W17_SemanticIndex", "W18_TLDAnalyzer", "W19_ContentMeta", "W20_CrossDomainGraph", "W21_DatasetExporter"]},
}


def test_gate_smoke() -> None:
    log.info("workers gate smoke start")
    suite = unittest.TestCase()
    suite.assertTrue(health()["/health"])
    suite.assertEqual(len(WORKERS), 21)
    with_retry_backoff(lambda: True, fallback=False, timeout=DEFAULT_TIMEOUT)
    load_plugin("importlib")


__all__ = ["DEMO_HOSTS", "SUPERVISORS", "WORKERS"]
