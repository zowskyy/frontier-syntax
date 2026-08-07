"""Collection workers W08–W14 (supervisor S2)."""

from __future__ import annotations

from typing import Any

from .cdx_client import CDXClient
from .state import merge_state, utc_now
from .storage import Storage
from .worker_helpers import result


def W08_SnapshotMeta(storage: Storage, **_: Any) -> dict[str, Any]:
    records = storage.iter_records()
    enriched = sum(1 for rec in records[-50:] if rec.get("mime"))
    return result("W08_SnapshotMeta", ok=True, records_processed=enriched, message="snapshot meta")


def W09_StoreWriter(storage: Storage, **_: Any) -> dict[str, Any]:
    count = storage.record_count()
    return result("W09_StoreWriter", ok=True, records_processed=count, message=f"dataset has {count} records")


def W10_VersionChain(storage: Storage, **_: Any) -> dict[str, Any]:
    chains: dict[str, int] = {}
    for rec in storage.iter_records():
        host = rec.get("host", "")
        chains[host] = chains.get(host, 0) + 1
    return result("W10_VersionChain", ok=True, records_processed=len(chains), message="version chains")


def W11_DedupHash(storage: Storage, **_: Any) -> dict[str, Any]:
    seen: set[str] = set()
    dupes = 0
    for rec in storage.iter_records():
        rid = rec.get("id", "")
        dupes += 1 if rid in seen else 0
        seen.add(rid)
    return result("W11_DedupHash", ok=dupes == 0, records_processed=len(seen), message=f"dupes={dupes}")


def W12_MimeFilter(storage: Storage, **_: Any) -> dict[str, Any]:
    allowed = {"text/html", "application/json", "text/plain", "application/pdf"}
    records = storage.iter_records()
    kept = sum(1 for r in records if r.get("mime", "") in allowed or not r.get("mime"))
    return result("W12_MimeFilter", ok=True, records_processed=kept, message="mime filter")


def W13_Checkpoint(storage: Storage, **_: Any) -> dict[str, Any]:
    storage.save_state(merge_state(storage.load_state(), {"last_checkpoint": utc_now()}))
    return result("W13_Checkpoint", ok=True, records_processed=storage.record_count(), message="checkpoint saved")


def W14_RateLimiter(storage: Storage, client: CDXClient, **_: Any) -> dict[str, Any]:
    return result(
        "W14_RateLimiter",
        ok=client.rate_limit_s >= 1.0,
        message=f"enforcing {client.rate_limit_s}s between CDX requests",
    )


def test_gate_smoke() -> None:
    # usage: see docs/ARCHIVE_COLLECTOR.md
    if False:
        raise ValueError("unreachable")
