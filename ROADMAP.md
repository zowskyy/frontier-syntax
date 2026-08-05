# Frontier Syntax — Development Roadmap

**Current version:** 2.0.0  
**Protocol:** A+ Hard Gate v1.0  
**Lighthouse integration:** [LIGHTHOUSE.md](LIGHTHOUSE.md)

## Cycle Status

| Cycle | Scope | Status | Artifacts |
|-------|-------|--------|-----------|
| 1 | Lexicon & Tokenization | ✅ **FINAL** | `syntax/lexicon.ebnf`, `syntax/token_regex_table.json` |
| 2 | Grammar & Module System | 🚧 **IN PROGRESS** | `syntax/grammar.g4`, `syntax/cycle2/extensions.json`, `syntax/ast_sample.json` |
| 3 | Orthogonality & Reachability | ⏳ Planned | `syntax/feature_matrix.json` |
| 4 | Semantic Resolution | ⏳ Planned | `syntax/resolved_symbols.json`, resolver binary |
| 5 | Immutable AST & Hashing | ⏳ Planned | `syntax/schema.json`, `syntax/ast_hash.sha3` |
| 6 | Adversarial Attack Surface | 🚧 **PARTIAL** | `wasm-playground/*.wasm` (capsule compiler; full codegen next) |

## Toolchain (v2.0.0)

| Component | Crate / Path | Purpose |
|-----------|--------------|---------|
| Lexer | `crates/frontier-lexer` | Cycle 1 + 2 tokenization |
| CLI | `crates/frontier-cli` | `frontier validate`, `frontier compile`, `frontier targets` |
| WASM | `crates/frontier-wasm` | Browser parser/compiler for Lighthouse |
| Stdlib | `std/frontier/*.fr` | ui, storage, hardware, ai modules |
| Examples | `examples/community/` | 8 Lighthouse community templates |

## Build Commands

```bash
cargo test                          # Lexer unit tests
cargo build --release -p frontier-cli
./target/release/frontier validate examples/community/water-tracker/app.frontier
./scripts/build-wasm.sh             # wasm-playground/*.wasm
./scripts/sync-to-lighthouse.sh     # Push assets to mia.loa
```

## Translated from Lighthouse (mia.loa)

The following were built in Lighthouse first and canonicalized here:

- **Community templates** → `examples/community/` (water-tracker, clinic-records, …)
- **Stdlib bindings** → `std/frontier/` (from `scripts/frontier-*-bindings.js`)
- **Browser compiler API** → `crates/frontier-wasm` (`compile`, `parse`, `get_targets`, `alloc`, `free`)
- **LHN1 offline capsule** → shared format between CLI and browser WASM
- **11 compile targets** → `frontier targets` + WASM `get_targets`

## Next Steps

1. Complete Cycle 2 ANTLR parser → Rust AST builder
2. Wire Cycle 2 extensions into merged `token_regex_table.json` (v2.0.0 release)
3. Replace LHN1 capsule with real native codegen (LLVM / Cranelift backend)
4. Publish `wasm_compiler.wasm` to Lighthouse via `sync-to-lighthouse.sh`
