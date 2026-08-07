# Frontier Syntax

[![A+ Hard Gate](https://github.com/zowskyy/frontier-syntax/actions/workflows/a-plus-hard-gate.yml/badge.svg)](https://github.com/zowskyy/frontier-syntax/actions/workflows/a-plus-hard-gate.yml)

Formally verifiable programming language — **A+ Hard Gate Certified** (`v1.0.0-a-plus-certified`).

## Status: ALL 16 PHASES PASS

See [FINAL_CERTIFICATION.md](FINAL_CERTIFICATION.md) for full certification details.

| Phase | Scope | Status |
|-------|-------|--------|
| 1–6 | Core Audit Cycles | PASS |
| 7 | LSP + VSCode Extension | PASS |
| 8 | LLVM Codegen (inkwell) | PASS |
| 9 | Interactive REPL | PASS |
| 10 | Package Manager | PASS |
| 11 | Coq Formal Prover | PASS |
| 12 | Documentation Generator | PASS |
| 13 | Performance Benchmarks | PASS |
| 14 | WASM Playground | PASS |
| 15 | CI/CD Pipeline | PASS |
| 16 | Release Packaging | PASS |

## Quick Start

```bash
# Full audit (all 16 phases)
bash scripts/full_audit.sh build.log

# Build tools
cargo build --release --bin frontier
cargo build --release --bin lsp
cargo build --release --bin repl

# Parse, compile, REPL
cargo run --release --bin frontier -- parse examples/sample.fr
cargo run --release --bin frontier -- compile examples/compile_test.fr -o examples/sample.o
clang examples/sample.o -o examples/sample && ./examples/sample  # exit 8
cargo run --release --bin repl
```

## Cryptographic Hashes (Immutable)

- **final_hash.sha3:** `4526dc37ea9d2b11a3c75fe1f3b262a246a11a3d972afeafcbc9865e456bd3e6`
- **ast_hash.sha3:** `3d5286d6079167b31d2e1c720da8af63eafe56d28666f0862f04abf02932b53f`

## Cursor Gate (Agent Policy)

Code changes are reviewed by dual gate scripts before merge. Bootstrapped from the Schema kit:

```bash
bash scripts/install-agent-environment.sh
bash scripts/gate-file.sh --file samples/hello_passing.py
bash scripts/gate-all-changed.sh
```

| Artifact | Role |
|----------|------|
| `cursor_gate.py` / `cursor_gate_fastest.py` | Dual reviewers (15 gates each) |
| `AGENTS.md` | Agent completion policy |
| `.cursor/rules/*.mdc` | Quarterback/worker delegation rules |
| `.github/workflows/gate-check.yml` | CI gate on pull requests |
| `samples/hello_passing.py` | Smoke-test fixture that passes all gates |

> Blueprint issues #44–#48 remain open; the gate layer itself is production-ready.

## License

MIT
