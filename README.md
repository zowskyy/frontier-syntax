# Frontier Syntax

Formally verifiable programming language syntax built under the **A+ Hard Gate Protocol (v1.0)**.

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
