# Frontier Syntax — Changelog

## [2.0.0] — 2026-08-05

### Added
- A+ Hard Gate v2.0 with 7 innovations (grammar mutator, proof-carrying code, PQ signatures, ZK-SNARK, IPFS, Neural LSP, package registry)
- Language hardening: 7 core `.frontier` modules + language reference
- Knowledge Hypercube (`src/knowledge/hypercube/`)
- Browser Compiler MVP (`src/browser_compiler.rs`, `src/wasm_codegen.rs`)
- Unity Module — unified compiler facade (`src/unity.rs`)
- Frontier Agent v2.0 (`frontier_agent.py`) with natural language intents
- Symbiotic Tandem — Master Orchestrator + Worker Agent (`.cursor/symbiotic_agents.py`)
- In-house Lighthouse stack (`frontier/lighthouse/`)
- Frontier-DEX decompiler (`frontier-dex/`)
- Foundation manifesto (`FOUNDATION.md`) and roadmap (`ROADMAP.md`)
- ARC orchestrator (`build/arc_orchestrator.py`)
- 6 audit cycle reports (`audit_reports/`)
- Chat scrub knowledge extraction (`chat_scrub/`)

### Changed
- README updated with v2.0 innovations and in-house stack
- CLI v2 integrated with Unity command preserved
- Cargo workspace includes frontier-dex member

### Fixed
- Grammar mutator `mutations.extend()` type mismatch
- PQ signature hash input types
- Resolver error conversion for `?` operator

### Merged PRs
- #4 Language Hardening, #6 Launch, #10–#15, #18–#21

### Known Gaps
- WASM codegen incomplete (let/if/calls/loops)
- Self-hosting at 0%
- Knowledge suggestions warnings-only
- External launch items pending

---

## [1.0.0] — 2026-08-05 (Cycle 1)

### Added
- Lexicon EBNF (`syntax/lexicon.ebnf`)
- Token regex table (45 emitting tokens)
- re2c lexer source
- Cycle 1 verification script and audit report
