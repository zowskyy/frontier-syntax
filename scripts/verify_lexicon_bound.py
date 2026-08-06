#!/usr/bin/env python3
"""ARC gates for Lexicon-Bound Worker deployment."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lexicon_bound_worker import LexiconBoundWorker  # noqa: E402

REQUIRED_FR = [
    "frontier/lexicon/tag.fr",
    "frontier/lexicon/core.fr",
    "frontier/worker/lexicon_bound.fr",
    "frontier/lexicon/user_ticket.fr",
    "frontier/lexicon/hard_gate.fr",
]

REQUIRED_SCRIPTS = [
    "scripts/lexicon_bound_worker.py",
    "scripts/lexicon_ingest.py",
    "scripts/lexicon_export.py",
]


def gate_files_exist() -> tuple[bool, str]:
    missing = [p for p in REQUIRED_FR + REQUIRED_SCRIPTS if not (ROOT / p).exists()]
    if missing:
        return False, f"Missing: {', '.join(missing)}"
    return True, "All Lexicon files present"


def gate_action_creates_entry() -> tuple[bool, str]:
    w = LexiconBoundWorker("arc_gate_tester", user_id="arc_reviewer")
    before = len(w._entries)
    result = w.execute_with_lexicon(
        action="arc_gate_test",
        input_data={"gate": "action_creates_entry"},
        documentation="ARC gate: verify action creates Lexicon entry",
        executor=lambda: {"pass": True, "status": "executed"},
    )
    entry = w.get_entry(result["lexicon_tag"])
    if not entry or not entry.get("documentation"):
        return False, "Action did not create documented Lexicon entry"
    return True, f"Action creates entry (tag={result['lexicon_tag'][:8]}...)"


def gate_user_ticket_bound() -> tuple[bool, str]:
    ticket = LexiconBoundWorker.create_user_ticket("arc_test_user")
    if not ticket.ticket_id or len(ticket.actions) < 1:
        return False, "User ticket not bound to Lexicon"
    close = ticket.close()
    if close.get("status") != "closed":
        return False, "Ticket close failed"
    return True, f"User ticket bound ({len(ticket.actions)} actions)"


def gate_queryable() -> tuple[bool, str]:
    w = LexiconBoundWorker("arc_query_tester")
    w.execute_with_lexicon(
        "query_test_action",
        {"query": "lexicon"},
        "Queryable test entry",
        lambda: {"pass": True},
    )
    hits = w.query("query_test")
    if not hits:
        return False, "Lexicon not queryable"
    return True, f"Lexicon queryable ({len(hits)} hits)"


def gate_exportable() -> tuple[bool, str]:
    import subprocess
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "lexicon_export.py")], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        return False, r.stderr[-200:]
    export_path = ROOT / "manifest" / "lexicon_export.json"
    if not export_path.exists():
        return False, "Export file not created"
    data = json.loads(export_path.read_text())
    if data.get("entry_count", 0) < 1:
        return False, "Export has no entries"
    return True, f"Exportable ({data['entry_count']} entries, {data.get('training_records', 0)} training records)"


def gate_hard_gate_enforced() -> tuple[bool, str]:
    if not (ROOT / "frontier/lexicon/hard_gate.fr").exists():
        return False, "hard_gate.fr missing"
    if not (ROOT / "docs" / "lexicon_log.fr").exists():
        return False, "lexicon_log.fr missing"
    # Every entry must have documentation
    index = ROOT / "manifest" / "lexicon_index.json"
    if index.exists():
        data = json.loads(index.read_text())
        for e in data.get("entries", []):
            if not e.get("documentation"):
                return False, f"Entry {e.get('action_id')} lacks documentation"
    return True, "Hard gate enforced — all entries documented"


GATES = [
    ("files_exist", gate_files_exist),
    ("action_creates_entry", gate_action_creates_entry),
    ("user_ticket_bound", gate_user_ticket_bound),
    ("lexicon_queryable", gate_queryable),
    ("lexicon_exportable", gate_exportable),
    ("hard_gate_enforced", gate_hard_gate_enforced),
]


def main() -> int:
    results = []
    all_pass = True
    for name, fn in GATES:
        try:
            ok, msg = fn()
        except Exception as exc:  # noqa: BLE001
            ok, msg = False, str(exc)
        results.append({"gate": name, "pass": ok, "message": msg})
        if not ok:
            all_pass = False
        print(f"{'PASS' if ok else 'FAIL'}: {name} — {msg}")

    manifest = ROOT / "manifest" / "lexicon_bound_arc.json"
    manifest.write_text(json.dumps({
        "all_pass": all_pass,
        "gates": results,
    }, indent=2), encoding="utf-8")

    if all_pass:
        print("\n✅ LEXICON-BOUND WORKER ARC GATES: ALL PASS")
        return 0
    print("\n❌ LEXICON-BOUND WORKER ARC GATES: FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
