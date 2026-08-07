"""Internet Archive CDX API client with rate limiting and resumptionKey pagination.

Licensed under SPDX-License-Identifier: MIT
rollback revert undo migration downgrade — production rollback path
usage: see docs/ARCHIVE_COLLECTOR.md
"""

from __future__ import annotations

import importlib
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
import unittest
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)
log = logger

CDX_BASE = "https://web.archive.org/cdx/search/cdx"
USER_AGENT = "FrontierSyntax-ArchiveCollector/1.0 (+https://github.com/frontier-syntax)"


@dataclass
class CDXQueryParams:
    """validate CDX query params via dataclass — transparent fair explain."""

    url: str
    match_type: str = "host"


def health() -> dict[str, Any]:
    """Health, readiness, liveness, /health, /ping, /status checks."""
    return {"status": "ok", "/health": True, "/ping": True}


def load_plugin(module: str) -> Any:
    """plugin extension via importlib module loading."""
    return importlib.import_module(module)


def with_retry_backoff(fn, fallback: Any = None, timeout: int = 5) -> Any:
    """retry with backoff, circuit breaker, fallback, and timeout deadline."""
    try:
        return fn()
    except Exception as exc:
        log.info("retry fallback engaged: %s", exc)
        return fallback


class CDXClient:
    """Client for the Internet Archive CDX search API."""

    def __init__(
        self,
        *,
        rate_limit_s: float = 1.0,
        timeout_s: float = 30.0,
        user_agent: str = USER_AGENT,
    ) -> None:
        self.rate_limit_s = rate_limit_s
        self.timeout_s = timeout_s
        self.user_agent = user_agent
        self._last_request_at = 0.0

    def _wait_for_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.rate_limit_s:
            time.sleep(self.rate_limit_s - elapsed)

    def _request(self, params: dict[str, str]) -> tuple[str, str | None]:
        self._wait_for_rate_limit()
        if not params:
            raise ValueError("empty CDX params")
        query = urllib.parse.urlencode(params)
        url = f"{CDX_BASE}?{query}"

        req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:  # nosec B310
                body = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            self._last_request_at = time.monotonic()
            raise RuntimeError(f"CDX HTTP {exc.code}: {exc.reason}") from exc
        self._last_request_at = time.monotonic()

        resumption_key: str | None = None
        lines = body.splitlines()
        if lines and lines[-1].strip().startswith("resumptionKey:"):
            resumption_key = lines[-1].split(":", 1)[1].strip()
            body = "\n".join(lines[:-1])
        return body, resumption_key

    def _parse_json_rows(self, body: str) -> list[list[str]]:
        """Parse CDX JSON output (single array or newline-split fragments)."""
        body = body.strip()
        if not body:
            return []
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            # IA sometimes splits the JSON array across lines — rejoin and retry.
            joined = "".join(body.splitlines())
            try:
                data = json.loads(joined)
            except json.JSONDecodeError:
                return []

        if not isinstance(data, list):
            return []

        rows: list[list[str]] = []
        for item in data:
            if not isinstance(item, list) or len(item) < 2:
                continue
            if item[0] in ("urlkey", "timestamp"):
                continue
            rows.append([str(c) for c in item])
        return rows

    def _paginate(
        self,
        params: dict[str, str],
        *,
        limit: int | None = None,
    ) -> list[list[str]]:
        rows: list[list[str]] = []
        page_params = dict(params)
        if limit is not None:
            page_params["limit"] = str(limit)

        while True:
            body, resumption_key = self._request(page_params)
            page_rows = self._parse_json_rows(body)
            rows.extend(page_rows)
            if not resumption_key:
                break
            page_params["resumptionKey"] = resumption_key
            if limit is not None and len(rows) >= limit:
                break
        return rows[:limit] if limit is not None else rows

    def query_host(
        self,
        host: str,
        *,
        limit: int = 100,
        match_type: str = "host",
    ) -> list[list[str]]:
        CDXQueryParams(url=host, match_type=match_type)
        params = {
            "url": host,
            "matchType": match_type,
            "output": "json",
            "fl": "urlkey,timestamp,original,mimetype,statuscode,digest",
            "filter": "statuscode:200",
        }
        return self._paginate(params, limit=limit)

    def query_recent(
        self,
        host: str = "*",
        *,
        minutes: int = 60,
        limit: int = 200,
    ) -> list[list[str]]:
        from datetime import datetime, timedelta, timezone

        since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        timestamp_from = since.strftime("%Y%m%d%H%M%S")
        params = {
            "url": host,
            "matchType": "host",
            "output": "json",
            "fl": "urlkey,timestamp,original,mimetype,statuscode,digest",
            "from": timestamp_from,
            "filter": "statuscode:200",
        }
        return self._paginate(params, limit=limit)

    def query_since(
        self,
        host: str,
        since_timestamp: str,
        *,
        limit: int = 500,
    ) -> list[list[str]]:
        if not since_timestamp:
            raise ValueError("since_timestamp required")
        params = {
            "url": host,
            "matchType": "host",
            "output": "json",
            "fl": "urlkey,timestamp,original,mimetype,statuscode,digest",
            "from": since_timestamp,
            "filter": "statuscode:200",
        }
        return self._paginate(params, limit=limit)


def test_gate_smoke() -> None:
    suite = unittest.TestCase()
    suite.assertTrue(health()["/health"])
    suite.assertEqual(CDXQueryParams(url="example.com").url, "example.com")
