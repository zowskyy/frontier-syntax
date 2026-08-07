#!/usr/bin/env python3
"""Empirical verification of all 7 Frontier v2 innovations (Phase 4 gate)."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifest" / "innovations_verify.json"

INNOVATIONS = [
    {
        "id": 1,
        "name": "Self-mutating grammar",
        "module": "grammar::",
        "path": "src/grammar/mutator.rs",
    },
    {
        "id": 2,
        "name": "Proof-carrying code",
        "module": "compiler::proof_generator::",
        "path": "src/compiler/proof_generator.rs",
    },
    {
        "id": 3,
        "name": "Post-quantum signatures",
        "module": "pq_signatures::",
        "path": "src/pq_signatures.rs",
    },
    {
        "id": 4,
        "name": "ZK-SNARK verification",
        "module": "zk::verifier::",
        "path": "src/zk/verifier.rs",
    },
    {
        "id": 5,
        "name": "IPFS imports",
        "module": "ipfs::resolver::",
        "path": "src/ipfs/resolver.rs",
    },
    {
        "id": 6,
        "name": "Neural LSP",
        "module": "neural::completion::",
        "path": "src/neural/completion.rs",
    },
    {
        "id": 7,
        "name": "Decentralized packages",
        "module": "packages::registry::",
        "path": "src/packages/registry.rs",
    },
]


def run_cargo_test(module: str) -> dict:
    cmd = ["cargo", "test", "--lib", module]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "pass": r.returncode == 0,
        "exit_code": r.returncode,
        "command": " ".join(cmd),
        "output": (r.stdout + r.stderr)[-600:],
    }


def verify() -> dict:
    results = []
    all_ok = True
    for inv in INNOVATIONS:
        path_ok = (ROOT / inv["path"]).exists()
        test = run_cargo_test(inv["module"]) if path_ok else {"pass": False, "output": "missing source"}
        ok = path_ok and test["pass"]
        if not ok:
            all_ok = False
        results.append(
            {
                "id": inv["id"],
                "name": inv["name"],
                "path": inv["path"],
                "source_present": path_ok,
                "tests_pass": test.get("pass", False),
                "pass": ok,
                "command": test.get("command"),
                "output": test.get("output"),
            }
        )

    feature_matrix = ROOT / "syntax" / "feature_matrix_v2.json"
    fm_ok = False
    if feature_matrix.exists():
        data = json.loads(feature_matrix.read_text(encoding="utf-8"))
        fm_ok = data.get("status") == "PASS"

    summary = {
        "verified_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "script": "scripts/verify_innovations.py",
        "innovations_pass": sum(1 for r in results if r["pass"]),
        "innovations_total": len(INNOVATIONS),
        "feature_matrix_pass": fm_ok,
        "pass": all_ok and fm_ok,
        "results": results,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    summary = verify()
    print(json.dumps(summary, indent=2))
    if summary["pass"]:
        print(f"PASS: {summary['innovations_pass']}/{summary['innovations_total']} innovations verified")
    else:
        print("FAIL: innovation verification")
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
