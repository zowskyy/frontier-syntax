# Frontier-DEX 2.0

Formally verified Android DEX decompiler built as ten incremental slices inside the Frontier Syntax workspace. The pipeline parses DEX bytecode, lifts it through SSA IR and AST recovery, optimizes, and emits Java 21 source.

## Usage

```bash
# Build release binary (from repo root)
cargo build --release -p frontier-dex

# Decompile a DEX file
./target/release/frontier-dex --input classes.dex

# Write .java files to a directory
./target/release/frontier-dex -i classes.dex -o ./out

# Optional flags
./target/release/frontier-dex -i classes.dex \
  --generate-proof \   # emit SHA3 proof hash
  --neural \           # obfuscation predictor
  --cache \            # content-addressable cache
  --fallback \         # CFR/Procyon/Fernflower fallback chain
  --json               # structured JSON output
```

**Web GUI** (React scaffold):

```bash
cd gui && npm install && npm run dev
```

## Architecture (10 Slices)

| Slice | Module(s) | Gate |
|-------|-----------|------|
| S-01 | `parser` | DEX header + map parse, `HybridNode` root |
| S-02 | `parser` | `class_defs` + `method_ids` linked to graph |
| S-03 | `ir` | CFG + phi nodes for all methods |
| S-04 | `ast` | If / Loop / Switch recovery from IR |
| S-05 | `optimizer` | Constant fold + block simplify |
| S-06 | `optimizer` | Fixed-point IR↔AST convergence |
| S-07 | `pretty` | Valid Java 21 source emission |
| S-08 | `engines` | CFR / Procyon / Fernflower fallback |
| S-09 | `cache` | Content-addressable hit/miss |
| S-10 | `main`, `gui/` | CLI + React UI end-to-end |

Data flow:

```
DEX bytes → parser (HybridGraph) → ir (SSA/CFG) → ast (patterns)
         → optimizer (fixed-point) → pretty (Java 21) → output
         ↔ engines (fallback) · cache · neural · verifier
```

Slice status and evidence live in `TRACKING.json`; events in `TRACKING_EVENTS.jsonl`.

## Build & Test

```bash
# From repo root
cargo build -p frontier-dex
cargo test -p frontier-dex              # lib + integration (25 tests)
cargo test -p frontier-dex --lib          # unit tests only
cargo test -p frontier-dex --test integration

# Benchmark gate (simulated metrics)
./frontier-dex/benchmark.sh

# Close-out (verify + seal tracking)
./frontier-dex/closeout.sh
```

## Honesty: Stubs & Limitations

This module implements a **working scaffold**, not a production JADX replacement. The following are intentionally stubbed or simulated:

| Area | Reality |
|------|---------|
| **Formal proofs** (`proofs/*.v`) | Coq artifacts present; not executed in CI (`coqc` gate is stub). |
| **ZK circuits** (`zk/*.zk`) | Placeholder files; `ark-crypto verify` not wired. |
| **Proof verifier** (`verifier.rs`) | SHA3 hashes over inputs, not cryptographic ZK proofs. |
| **Fallback engines** (`engines.rs`) | JNI stubs return placeholder Java; CFR/Procyon/Fernflower not invoked. |
| **IPFS** (`cache.rs`) | `pin_ipfs_stub` returns synthetic `ipfs://Qm…` URIs; no daemon. |
| **LMDB** | File-backed JSON cache in temp dir, not LMDB. |
| **Benchmark** (`benchmark.sh`) | Prints simulated 10× metrics; does not run JADX. |
| **Neural predictor** (`neural.rs`) | Heuristic scoring from `assets/obfuscation_patterns.json`. |
| **GUI** (`gui/`) | Vite/React scaffold; no live decompile API wired. |

Unit tests (23 lib + 2 integration) exercise the in-tree pipeline on synthetic DEX fixtures. Passing gates in `TRACKING.json` reflect those tests and stub evidence, not independent formal verification.

## Related Files

- `TRACKING.json` — slice and gate status
- `TRACKING_EVENTS.jsonl` — append-only event log
- `CERTIFICATION.md` — filled by `verify.sh` at close-out
- `closeout.sh` — runs verify, seals project as closed
