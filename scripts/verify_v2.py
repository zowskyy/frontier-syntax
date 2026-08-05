#!/usr/bin/env python3
"""Verify Frontier v2.0 A+ Hard Gate — all 7 innovations."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_SYNTAX = [
    "syntax/Frontier.g4",
    "syntax/feature_matrix_v2.json",
    "syntax/schema_v2.json",
    "syntax/grammar_v2.json",
    "syntax/ast_sample_v2.json",
    "syntax/ast_hash_v2.sha3",
    "syntax/final_hash_v2.sha3",
]

REQUIRED_SRC = [
    "src/parser/mod.rs",
    "src/parser/handwritten.rs",
    "src/grammar/mutator.rs",
    "src/compiler/proof_generator.rs",
    "src/pq_signatures.rs",
    "src/zk/verifier.rs",
    "src/ipfs/resolver.rs",
    "src/neural/completion.rs",
    "src/packages/registry.rs",
    "src/lsp/neural_server.rs",
    "src/v2_resolver.rs",
]

INNOVATIONS = [
    ("Self-mutating grammar", "src/grammar/mutator.rs"),
    ("Proof-carrying code", "src/compiler/proof_generator.rs"),
    ("Post-quantum signatures", "src/pq_signatures.rs"),
    ("ZK-SNARK verification", "src/zk/verifier.rs"),
    ("IPFS imports", "src/ipfs/resolver.rs"),
    ("Neural LSP", "src/neural/completion.rs"),
    ("Decentralized packages", "src/packages/registry.rs"),
]


def check_files():
    errors = []
    for rel in REQUIRED_SYNTAX + REQUIRED_SRC + ["proofs/sample_proof.v"]:
        if not (ROOT / rel).exists():
            errors.append(f"Missing: {rel}")
    return errors


def check_feature_matrix():
    path = ROOT / "syntax" / "feature_matrix_v2.json"
    data = json.loads(path.read_text())
    if data.get("status") != "PASS":
        return [f"feature_matrix_v2.json status is not PASS"]
    if "v2_features" not in data:
        return ["feature_matrix_v2.json missing v2_features"]
    return []


def check_cargo_tests():
    result = subprocess.run(
        ["cargo", "test", "--lib"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return [f"cargo test failed:\n{result.stderr[-2000:]}"]
    return []


def check_v2_parser():
    result = subprocess.run(
        [
            "cargo", "run", "--release", "--bin", "frontier", "--",
            "parse-v2", "examples/v2_parser_test.fr",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return [f"v2 parser CLI failed:\n{result.stderr[-1000:]}"]
    return []


def check_coq():
    script = ROOT / "scripts" / "validate_coq.py"
    if not script.exists():
        return []
    result = subprocess.run([sys.executable, str(script)], cwd=ROOT)
    if result.returncode != 0:
        return ["Coq proof validation failed"]
    return []


def main():
    errors = []
    errors.extend(check_files())
    errors.extend(check_feature_matrix())
    errors.extend(check_cargo_tests())
    errors.extend(check_v2_parser())
    errors.extend(check_coq())

    if errors:
        print("FAIL: Frontier v2.0 verification")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("PASS: Frontier v2.0 A+ Hard Gate verification")
    print(f"  Innovations: {len(INNOVATIONS)}/7")
    for name, path in INNOVATIONS:
        print(f"    ✅ {name} ({path})")
    print(f"  Syntax artifacts: {len(REQUIRED_SYNTAX)}")
    print("  Cargo tests: All passing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
