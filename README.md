# Frontier Syntax

Formally verifiable programming language syntax built under the **A+ Hard Gate Protocol (v1.0)**.

## Status: ALL CYCLES PASS

| Cycle | Scope | Status |
|-------|-------|--------|
| 1 | Lexicon & Tokenization | PASS |
| 2 | Grammar & Associativity | PASS |
| 3 | Orthogonality & Reachability | PASS |
| 4 | Semantic Resolution | PASS |
| 5 | Immutable AST & Hashing | PASS |
| 6 | Adversarial Attack Surface | PASS |

## Quick Start

```bash
# Verify all cycles
bash scripts/run_all_cycles.sh

# Parse a program
cargo run --release -- parse examples/sample.fr

# Resolve symbols
cargo run --release -- resolve examples/sample.fr

# Compute AST hash
cargo run --release -- hash examples/sample.fr
```

## Artifacts

| Artifact | Path |
|----------|------|
| Lexicon EBNF | `syntax/lexicon.ebnf` |
| Token Regex Table | `syntax/token_regex_table.json` |
| ANTLR Grammar | `syntax/Frontier.g4` (link: `syntax/grammar.g4`) |
| AST Sample | `syntax/ast_sample.json` |
| Feature Matrix | `syntax/feature_matrix.json` |
| Resolved Symbols | `syntax/resolved_symbols.json` |
| AST Schema | `syntax/schema.json` |
| AST Hash | `syntax/ast_hash.sha3` |
| WASM Parser | `syntax/wasm_parser.wasm` |
| Final Hash | `syntax/final_hash.sha3` |

## Toolchain

| Component | Tool | Version |
|-----------|------|---------|
| Lexer | re2c | 3.1 |
| Parser Grammar | ANTLR | 4.13.1 |
| Parser/Resolver | Rust | 1.83.0 |
| Hash | SHA-3-256 | NIST FIPS 202 |
| WASM | wasm-pack | 0.13.1 |

## Cryptographic Hashes

- **AST Hash:** `3d5286d6079167b31d2e1c720da8af63eafe56d28666f0862f04abf02932b53f`
- **Final Hash:** `4526dc37ea9d2b11a3c75fe1f3b262a246a11a3d972afeafcbc9865e456bd3e6`

## Audit Reports

Reports for each cycle are in `audit_reports/cycle_N_report.md`.

## License

MIT
