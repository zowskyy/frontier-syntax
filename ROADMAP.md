# Frontier Roadmap — Phase 0–10

**Foundation ID:** frontier-v2.0.0  
**Template:** Shared across all Frontier projects  
**Gate status (main, 2026-08-07):** Phases 0–3 validated · Phases 4–10 frozen

---

## Phases

| Phase | Name | Status | Description |
|-------|------|--------|-------------|
| 0 | Foundation | ✅ Validated | Manifesto, hypercube, global skills, verification protocol |
| 1 | Real WASM Codegen | ✅ Validated | let, if, calls, loops, return — wasmtime 4/4 |
| 2 | Knowledge → Codegen | ✅ Validated | Algorithm suggestions change emitted WASM |
| 3 | Unified Glue + Slim WASM | ✅ Validated | wasm-slim 93 KB (&lt;100 KB target) |
| 4 | Spec vs Impl (innovations) | 🔒 Frozen | 7 innovation verification claims |
| 5 | True Self-Hosting | 🔒 Frozen | Frontier-native compiler (no Rust wrapper) |
| 6 | Neural LSP / LLM corpus | 🔒 Frozen | Production-grade completion + training data |
| 7 | Decentralized Packages | 🔒 Frozen | IPFS registry integration |
| 8 | Proof-Carrying Code | 🔒 Frozen | Coq proofs attached to compiled artifacts |
| 9 | Production Hardening | 🔒 Frozen | CI, security, performance at scale |
| 10 | Launch | 🔒 Frozen | External go-to-market items |

---

## Phase 1 — Real WASM Codegen (complete)

File: `src/wasm_codegen.rs`

- [x] P1 let bindings in WASM codegen
- [x] P1 if/else branches
- [x] P1 function calls
- [x] P1 while loops
- [x] P1 return expressions
- [x] P1 `cargo test --lib wasm_codegen::` (6 tests)
- [x] P1 wasmtime wast execution (4/4 cases)
- [ ] P1 floats, strings, structs in WASM (post-release)

## Phase 2 — Knowledge → Codegen (complete)

- [x] `test_knowledge_changes_wasm` passes
- [x] Issue #45 closed by independent validator

## Phase 3 — Slim WASM (complete)

- [x] wasm-slim build: 93.0 KB (`manifest/wasm_size.json`)
- [x] Issue #48 closed

Phases 4–10 remain frozen until explicitly unblocked in `PROJECT_BLUEPRINT.md`.

---

## Verification Gates

```bash
python3 scripts/tracking.py gate          # phases 0–3 must pass
.cursor/frontier_agent.sh gaps            # honest gap report
python3 build/arc_orchestrator.py --verify
```
