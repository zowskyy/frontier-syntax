# Frontier Foundation Manifesto

**Foundation ID:** frontier-v2.0.0  
**Status:** Active  
**Scope:** All Frontier Syntax projects share this foundation

---

## Core Principles

1. **Knowledge is Silent** — Intelligence is embedded in the toolchain, not scattered in comments.
2. **Code is Dense** — Every line earns its place; no ceremony without semantics.
3. **History is Embedded** — Decisions, proofs, and lineage live in verifiable artifacts.

---

## Global Skills (10 Commandments)

| # | Skill | Description |
|---|-------|-------------|
| 1 | Zero Ambiguity | Every construct has exactly one meaning |
| 2 | Formal Completeness | All language features are specified |
| 3 | Adversarial Resilience | Parsers and verifiers resist malformed input |
| 4 | Toolchain Specificity | Every tool and version is pinned |
| 5 | Verifiable Artifacts | All outputs are checkable by script |
| 6 | No Circular Dependencies | Cycles depend only on prior cycles |
| 7 | Implementation Ready | Specs map directly to code |
| 8 | Post-Audit Immutability | Audited artifacts cascade on change |
| 9 | Error Message Spec | Failures are actionable and consistent |
| 10 | Cryptographic Finality | Canonical forms hash to SHA-3-256 |

---

## Shared Foundation Components

Every Frontier project inherits:

- **Foundation Manifesto** — `FOUNDATION.md` (this file)
- **Knowledge Hypercube** — `src/knowledge/hypercube/`
- **Global Skills** — 10 commandments above
- **Roadmap Template** — `ROADMAP.md` (Phase 0–10)
- **Verification Protocol** — `frontier foundation verify` / `.cursor/frontier_agent.sh`
- **CLI Interface** — `frontier` binary with `compile`, `knowledge`, and foundation commands

---

## Correlation Commands

```bash
frontier foundation verify   # Verify project against foundation
frontier foundation hash       # Hash foundation artifacts
frontier foundation show       # Display foundation metadata
frontier foundation new <name> # Scaffold a new correlated project
```

---

## Verification

Run the complete context loader:

```bash
.cursor/frontier_context.sh
```

Then verify:

```bash
.cursor/frontier_agent.sh all
python3 build/arc_orchestrator.py --verify
```
