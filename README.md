# Frontier Syntax v2.0

Formally verifiable programming language — **A+ Hard Gate v2.0** with 7 innovations.

## Quick Start

```bash
# Full verification (Cycle 1 + Language Hardening + v2.0)
python3 build/arc_orchestrator.py --verify

# Run Rust tests (17 tests)
cargo test --lib

# Build WASM parser
cargo build --release --target wasm32-unknown-unknown

# Generate v2 hashes
python3 scripts/generate_v2_hashes.py
```

## v2.0 Innovations

| # | Innovation | Module |
|---|------------|--------|
| 1 | Self-mutating grammar | `src/grammar/mutator.rs` |
| 2 | Proof-carrying code | `src/compiler/proof_generator.rs` |
| 3 | Post-quantum signatures | `src/pq_signatures.rs` |
| 4 | ZK-SNARK AST verification | `src/zk/verifier.rs` |
| 5 | IPFS decentralized imports | `src/ipfs/resolver.rs` |
| 6 | Neural LSP | `src/neural/completion.rs` |
| 7 | Decentralized package registry | `src/packages/registry.rs` |

## Core Language (Hardened)

The standalone Frontier language core lives under `frontier/core/` — parser, type system, memory model, concurrency, error handling, standard library, and compiler backend.

## In-House Lighthouse Stack (100% Frontier)

**Everything is Frontier Syntax.** No JavaScript, Python, npm, or third-party app logic.

| Component | Source |
|-----------|--------|
| ARC Engine | `frontier/lighthouse/arc_engine.frontier` |
| Discovery Engine | `frontier/lighthouse/discovery_engine.frontier` |
| Agent Distiller | `frontier/lighthouse/agent_distiller.frontier` |
| Browser Compiler | `frontier/lighthouse/browser_compiler.frontier` → `wasm_compiler.wasm` |
| FFI Bindings | `frontier/bindings/*.frontier` (ui, storage, ai, hardware, compiler, http) |
| Community App | `examples/lighthouse/water_pump_tracker.frontier` |

```bash
python3 scripts/verify_lighthouse_stack.py
```

See [docs/IN_HOUSE_STACK.md](docs/IN_HOUSE_STACK.md).

| Module | Path |
|--------|------|
| Parser (Lexer → AST) | `frontier/core/parser.frontier` |
| Type System | `frontier/core/types.frontier` |
| Memory Model | `frontier/core/memory.frontier` |
| Concurrency | `frontier/core/concurrency.frontier` |
| Error Handling | `frontier/core/errors.frontier` |
| Standard Library | `frontier/core/stdlib.frontier` |
| Compiler Backend | `frontier/core/compiler.frontier` |
| Language Reference | `frontier/docs/language_reference.md` |

## Protocol

All syntax artifacts are produced in six audit cycles. Each cycle must pass all ten hard-gate criteria before the next cycle begins.

| Cycle | Scope | Primary Artifacts |
|-------|-------|-------------------|
| 1 | Lexicon & Tokenization | `syntax/lexicon.ebnf`, `syntax/token_regex_table.json` |
| 2 | Grammar & Associativity | `syntax/Frontier.g4`, `syntax/ast_sample_v2.json` |
| 3 | Orthogonality & Reachability | `syntax/feature_matrix_v2.json` |
| 4 | Semantic Resolution | `src/v2_resolver.rs`, `src/resolver.rs` |
| 5 | Immutable AST & Hashing | `syntax/schema_v2.json`, `syntax/ast_hash_v2.sha3` |
| 6 | Adversarial Attack Surface | `syntax/wasm/wasm_parser_v2.wasm`, `syntax/final_hash_v2.sha3` |

## Toolchain

| Component | Tool | Version |
|-----------|------|---------|
| Lexer | re2c | 3.1 |
| Parser | ANTLR | 4.13.1 |
| Resolver | Rust | 1.75+ |
| Hash | SHA-3-256 | NIST FIPS 202 |
| WASM | wasm-pack | 0.12+ |

## Encoding

All source files **must** be UTF-8. Input **must** be NFC-normalized before lexing.

## License

MIT
