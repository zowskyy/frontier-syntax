# Frontier Syntax

Formally verifiable programming language built under the **A+ Hard Gate Protocol (v1.0)**. Powers [Lighthouse](https://github.com/zowskyy/mia.loa) in-browser native compilation.

**Version 2.0.0** — Cycle 2 module system, Rust toolchain, WASM browser compiler, community examples.

## Quick Start

```bash
# Validate a program
cargo build --release -p frontier-cli
./target/release/frontier validate examples/community/water-tracker/app.frontier

# List compile targets (used by Lighthouse download menu)
./target/release/frontier targets

# Build WASM for Lighthouse browser-compiler.js
./scripts/build-wasm.sh
LIGHTHOUSE_HOME=/path/to/mia.loa ./scripts/sync-to-lighthouse.sh
```

## Protocol Cycles

| Cycle | Scope | Status | Artifacts |
|-------|-------|--------|-----------|
| 1 | Lexicon & Tokenization | ✅ FINAL | `syntax/lexicon.ebnf`, `syntax/token_regex_table.json` |
| 2 | Grammar & Module System | 🚧 IN PROGRESS | `syntax/grammar.g4`, `syntax/cycle2/extensions.json` |
| 3 | Orthogonality | ⏳ Planned | `syntax/feature_matrix.json` |
| 4 | Semantic Resolution | ⏳ Planned | resolver binary |
| 5 | Immutable AST & Hashing | ⏳ Planned | `syntax/schema.json` |
| 6 | WASM Attack Surface | 🚧 PARTIAL | `wasm-playground/*.wasm` |

See [ROADMAP.md](ROADMAP.md) for full progress.

## Rust Toolchain

| Crate | Binary / Output | Purpose |
|-------|-----------------|---------|
| `frontier-lexer` | library | Cycle 1 + 2 tokenization |
| `frontier-cli` | `frontier` | validate, compile, targets |
| `frontier-wasm` | `wasm_compiler.wasm` | Lighthouse browser compiler |

## Standard Library

| Module | Path | Replaces |
|--------|------|----------|
| `frontier.ui` | `std/frontier/ui.fr` | Capacitor / WebView |
| `frontier.storage` | `std/frontier/storage.fr` | SQLite + offline sync |
| `frontier.hardware` | `std/frontier/hardware.fr` | GPS, camera, barcode |
| `frontier.ai` | `std/frontier/ai.fr` | WebLLM → llama.cpp FFI |

## Community Examples

Eight Lighthouse templates in `examples/community/`:

🚰 water-tracker · 🏥 clinic-records · 🌾 market-prices · 📚 school-attendance  
📦 inventory-manager · 💰 community-ledger · 📋 field-survey · 🎉 event-planner

## Lighthouse Integration

See [LIGHTHOUSE.md](LIGHTHOUSE.md) for sync scripts, WASM API contract, and LHN1 capsule format.

## Verification

```bash
python3 scripts/verify_cycle1.py
python3 scripts/verify_cycle2.py
cargo test
```

## Encoding

All source files **must** be UTF-8. Input **must** be NFC-normalized before lexing.

## License

MIT
