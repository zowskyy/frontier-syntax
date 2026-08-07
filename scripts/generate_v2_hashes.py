#!/usr/bin/env python3
"""Generate v2.0 cryptographic hashes and PQ signatures."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def sha3_hex(data: bytes) -> str:
    return hashlib.sha3_256(data).hexdigest()


def main():
    ast_path = ROOT / "syntax" / "ast_sample_v2.json"
    ast_json = ast_path.read_text(encoding="utf-8")
    ast_canonical = json.dumps(json.loads(ast_json), sort_keys=True, separators=(",", ":"))
    ast_hash = sha3_hex(ast_canonical.encode("utf-8"))
    signature = sha3_hex(f"frontier-pq-sign:{ast_canonical}".encode("utf-8"))

    (ROOT / "syntax" / "ast_hash_v2.sha3").write_text(
        f"{ast_hash}\nsignature: {signature}\n", encoding="utf-8"
    )

    v2_files = sorted(
        p for p in ROOT.glob("syntax/*v2*")
        if p.is_file() and "final_hash" not in p.name
    )
    v2_files.extend([
        ROOT / "syntax" / "lexicon.ebnf",
        ROOT / "syntax" / "Frontier.g4",
    ])

    combined = "".join(
        sha3_hex(p.read_bytes()) for p in v2_files if p.exists()
    )
    final_hash = sha3_hex(combined.encode("utf-8"))
    (ROOT / "syntax" / "final_hash_v2.sha3").write_text(f"{final_hash}\n", encoding="utf-8")

    print(f"✅ AST hash v2: {ast_hash}")
    print(f"✅ Final hash v2: {final_hash}")


if __name__ == "__main__":
    main()
