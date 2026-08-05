# Frontier Syntax

Formally verifiable programming language syntax built under the **A+ Hard Gate Protocol (v1.0)**.

## Core Language (Hardened)

The standalone Frontier language core lives under `frontier/core/` — parser, type system, memory model, concurrency, error handling, standard library, and compiler backend. Game-specific elements have been stripped.

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

```bash
# Verify hardened language
python3 build/arc_orchestrator.py --verify

# Test core modules
python3 scripts/frontier test frontier/core/

# Compile a test program
python3 scripts/frontier compile test_program.frontier
```

## Protocol

All syntax artifacts are produced in six audit cycles. Each cycle must pass all ten hard-gate criteria before the next cycle begins.

| Cycle | Scope | Primary Artifacts |
|-------|-------|-------------------|
| 1 | Lexicon & Tokenization | `syntax/lexicon.ebnf`, `syntax/token_regex_table.json` |
| 2 | Grammar & Associativity | `syntax/grammar.g4`, `syntax/ast_sample.json` |
| 3 | Orthogonality & Reachability | `syntax/feature_matrix.json` |
| 4 | Semantic Resolution | `syntax/resolved_symbols.json`, resolver binary |
| 5 | Immutable AST & Hashing | `syntax/schema.json`, `syntax/ast_hash.sha3` |
| 6 | Adversarial Attack Surface | `syntax/wasm_parser.wasm`, `syntax/final_hash.sha3` |

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
