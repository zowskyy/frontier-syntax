"""Discovery workers W01–W07 (supervisor S1)."""

from __future__ import annotations

from typing import Any

from .cdx_client import CDXClient
from .shadow_mirror import ShadowMirror
from .state import merge_state
from .storage import Storage
from .worker_helpers import DEMO_HOSTS, result, write_cdx_rows


def W01_CDXScanner(
    storage: Storage,
    client: CDXClient,
    *,
    hosts: list[str] | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    hosts = hosts or DEMO_HOSTS
    total = 0
    errors: list[str] = []
    for host in hosts:
        try:
            rows = client.query_host(host, limit=limit)
            total += write_cdx_rows(storage, rows, supervisor="S1", worker="W01_CDXScanner")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{host}: {exc}")
    return result(
        "W01_CDXScanner",
        ok=total > 0 or not errors,
        records_processed=total,
        message=f"scanned {len(hosts)} hosts",
        errors=errors,
    )


def W02_DomainShard(
    storage: Storage,
    client: CDXClient,
    *,
    hosts: list[str] | None = None,
    shard_index: int = 0,
    shard_count: int = 1,
) -> dict[str, Any]:
    hosts = hosts or DEMO_HOSTS
    shard_hosts = [h for i, h in enumerate(hosts) if i % shard_count == shard_index]
    total = 0
    for host in shard_hosts:
        try:
            rows = client.query_host(host, limit=5)
            total += write_cdx_rows(storage, rows, supervisor="S1", worker="W02_DomainShard")
        except Exception:  # noqa: BLE001
            continue
    return result(
        "W02_DomainShard",
        ok=True,
        records_processed=total,
        message=f"shard {shard_index}/{shard_count}: {len(shard_hosts)} hosts",
    )


def W03_ResumptionWalker(
    storage: Storage,
    client: CDXClient,
    *,
    host: str = "archive.org",
    limit: int = 20,
) -> dict[str, Any]:
    state = storage.load_state()
    key = f"W03:{host}"
    since = state.get("resumption_keys", {}).get(key)
    try:
        rows = client.query_since(host, since, limit=limit) if since else client.query_host(host, limit=limit)
        written = write_cdx_rows(storage, rows, supervisor="S1", worker="W03_ResumptionWalker")
        if rows:
            last_ts = rows[-1][1] if len(rows[-1]) > 1 else since
            storage.save_state(merge_state(state, {"resumption_keys": {key: last_ts}}))
        return result("W03_ResumptionWalker", ok=True, records_processed=written, message=f"walked {host}")
    except Exception as exc:  # noqa: BLE001
        return result("W03_ResumptionWalker", ok=False, message=str(exc))


def W04_PolitenessGate(storage: Storage, client: CDXClient, **_: Any) -> dict[str, Any]:
    delay = client.rate_limit_s
    storage.save_state(merge_state(storage.load_state(), {"politeness_delay_s": delay}))
    return result("W04_PolitenessGate", ok=delay >= 1.0, message=f"rate limit {delay}s")


def W05_PrefixEnumerator(
    storage: Storage,
    client: CDXClient,
    *,
    host: str = "wikipedia.org",
    prefixes: list[str] | None = None,
) -> dict[str, Any]:
    prefixes = prefixes or ["wiki/", "w/"]
    total = 0
    for prefix in prefixes:
        try:
            rows = client.query_host(f"{host}/{prefix}", limit=5)
            total += write_cdx_rows(storage, rows, supervisor="S1", worker="W05_PrefixEnumerator")
        except Exception:  # noqa: BLE001
            continue
    return result("W05_PrefixEnumerator", ok=True, records_processed=total, message=f"prefixes on {host}")


def W06_NewCaptureWatcher(
    storage: Storage,
    client: CDXClient,
    *,
    host: str = "github.com",
    minutes: int = 1440,
) -> dict[str, Any]:
    try:
        rows = client.query_recent(host=host, minutes=minutes, limit=10)
        written = write_cdx_rows(storage, rows, supervisor="S1", worker="W06_NewCaptureWatcher")
        return result("W06_NewCaptureWatcher", ok=True, records_processed=written, message=f"watched {host}")
    except Exception as exc:  # noqa: BLE001
        return result("W06_NewCaptureWatcher", ok=True, message=f"watch deferred: {exc}")


def W07_ShadowMirror(storage: Storage, client: CDXClient, *, minutes: int = 60) -> dict[str, Any]:
    poll = ShadowMirror(storage=storage, client=client).poll_recent(minutes=minutes, limit=20)
    return result(
        "W07_ShadowMirror",
        ok=poll.get("ok", False),
        records_processed=poll.get("records_written", 0),
        message=f"shadow poll {poll.get('rows_fetched', 0)} rows",
        detail=poll,
    )


def test_gate_smoke() -> None:
    # usage: see docs/ARCHIVE_COLLECTOR.md
    if not DEMO_HOSTS:
        raise ValueError("missing demo hosts")
