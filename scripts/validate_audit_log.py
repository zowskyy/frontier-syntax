#!/usr/bin/env python3
"""Validate committed audit JSONL against schema, hash chain, and PII policy."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SESSIONS = REPO / "docs" / "agent_audit_log" / "sessions"
SCHEMA_PATH = REPO / "schemas" / "audit_entry.schema.json"

FORBIDDEN_FIELDS = {"user_prompt_excerpt"}


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_with_jsonschema(entry: dict, schema: dict) -> list[str]:
    try:
        import jsonschema
    except ImportError:
        return _minimal_validate(entry)
    validator = jsonschema.Draft202012Validator(schema)
    return [f"{e.json_path}: {e.message}" for e in validator.iter_errors(entry)]


def _minimal_validate(entry: dict) -> list[str]:
    errors: list[str] = []
    for req in (
        "id",
        "timestamp_utc",
        "session_id",
        "category",
        "action",
        "why",
        "how_to_repeat",
        "honesty",
    ):
        if req not in entry:
            errors.append(f"missing required field: {req}")
    if any(f in entry for f in FORBIDDEN_FIELDS):
        errors.append("forbidden field user_prompt_excerpt present (PII policy)")
    if entry.get("user_prompt_excerpt"):
        errors.append("user_prompt_excerpt must not be committed")
    return errors


def compute_entry_hash(entry: dict) -> str:
    payload = {k: v for k, v in entry.items() if k != "entry_hash"}
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def check_pii(entry: dict) -> list[str]:
    errors: list[str] = []
    for field in FORBIDDEN_FIELDS:
        if field in entry and entry[field]:
            errors.append(f"PII policy violation: {field} must not be in committed logs")
    return errors


def validate_file(path: Path, schema: dict, strict_hash: bool) -> tuple[int, list[str]]:
    errors: list[str] = []
    prev_hash: str | None = None
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"{path.name}:{i} invalid JSON: {e}")
            continue

        errors.extend(f"{path.name}:{i} {e}" for e in check_pii(entry))
        errors.extend(f"{path.name}:{i} {e}" for e in validate_with_jsonschema(entry, schema))

        if strict_hash and "entry_hash" in entry:
            expected = compute_entry_hash(entry)
            if entry["entry_hash"] != expected:
                errors.append(f"{path.name}:{i} entry_hash mismatch")
            if prev_hash is not None and entry.get("prev_hash") != prev_hash:
                errors.append(f"{path.name}:{i} prev_hash chain broken")
            prev_hash = entry["entry_hash"]
        elif prev_hash is None and i == 1:
            prev_hash = entry.get("entry_hash")

    return len(lines), errors


def main() -> int:
    p = argparse.ArgumentParser(description="Validate audit session JSONL files")
    p.add_argument("--sessions-dir", type=Path, default=SESSIONS)
    p.add_argument("--strict-hash", action="store_true", help="require hash chain on all entries")
    p.add_argument("--legacy-ok", action="store_true", help="allow entries without entry_hash")
    args = p.parse_args()

    if not SCHEMA_PATH.exists():
        print(f"Schema missing: {SCHEMA_PATH}", file=sys.stderr)
        return 1

    schema = load_schema()
    if not args.sessions_dir.exists():
        print(f"No sessions dir: {args.sessions_dir}")
        return 0

    total = 0
    all_errors: list[str] = []
    for path in sorted(args.sessions_dir.glob("*.jsonl")):
        n, errs = validate_file(path, schema, strict_hash=args.strict_hash and not args.legacy_ok)
        total += n
        all_errors.extend(errs)

    if all_errors:
        print(f"FAIL: {len(all_errors)} validation error(s) in {total} entries", file=sys.stderr)
        for e in all_errors[:50]:
            print(f"  {e}", file=sys.stderr)
        if len(all_errors) > 50:
            print(f"  ... and {len(all_errors) - 50} more", file=sys.stderr)
        return 1

    print(f"PASS: {total} entries validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
