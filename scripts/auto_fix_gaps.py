#!/usr/bin/env python3
"""Automated gap closure — create tracked work items and scaffold fixes for P0 gaps."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "chat_scrub" / "WORKER_REPORT.json"
FIXES_DIR = ROOT / "chat_scrub" / "gap_fixes"


GAP_ACTIONS = {
    "wasm_codegen_incomplete": {
        "action": "Extend src/wasm_codegen.rs with let/if/calls/loops/return",
        "verify": ["cargo", "test", "--lib", "wasm_codegen"],
        "scaffold": "src/wasm_codegen.rs",
    },
    "knowledge_warnings_only": {
        "action": "Wire AlgorithmSuggestion.implementation_hint into wasm_codegen.rs",
        "verify": ["cargo", "test", "--lib", "unity"],
        "scaffold": "src/knowledge_bridge.rs",
    },
    "self_hosting_zero": {
        "action": "Bootstrap parser from frontier/core/parser.frontier spec alignment",
        "verify": ["python3", "scripts/verify_language_hardening.py"],
        "scaffold": "frontier/core/parser.frontier",
    },
}


def main() -> int:
    if not REPORT.exists():
        print("FAIL: WORKER_REPORT.json not found — run scrub first")
        return 1

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    gaps = report.get("known_gaps", [])
    FIXES_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    for gap in gaps:
        gap_id = gap.get("id", "")
        priority = gap.get("priority", "P2")
        action = GAP_ACTIONS.get(gap_id, {})
        fix_plan = {
            "id": gap_id,
            "priority": priority,
            "description": gap.get("description", ""),
            "recommended_action": action.get("action", "Manual review required"),
            "scaffold_file": action.get("scaffold"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        plan_path = FIXES_DIR / f"{gap_id}.json"
        plan_path.write_text(json.dumps(fix_plan, indent=2), encoding="utf-8")
        results.append(fix_plan)

        if action.get("verify"):
            verify = subprocess.run(action["verify"], cwd=ROOT, capture_output=True, text=True)
            fix_plan["verify_passed"] = verify.returncode == 0
            fix_plan["verify_output"] = (verify.stdout or verify.stderr)[-200:]

    # Delegate issue creation to frontier_agent gap logic
    subprocess.run(
        [sys.executable, str(ROOT / "frontier_agent.py"), "Create issues from knowledge gaps"],
        cwd=ROOT,
        capture_output=True,
    )

    summary_path = FIXES_DIR / "summary.json"
    summary_path.write_text(json.dumps({"gaps": len(results), "plans": results}, indent=2), encoding="utf-8")
    print(f"✅ Gap closure plans: {len(results)} written to {FIXES_DIR.relative_to(ROOT)}")
    for r in results:
        print(f"  [{r['priority']}] {r['id']}: {r['recommended_action'][:60]}...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
