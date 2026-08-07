# Frontier Roadmap — Phase 0–10

**Foundation ID:** frontier-v2.0.0  
**Template:** Shared across all Frontier projects

---

## Phases

| Phase | Name | Status | Description |
|-------|------|--------|-------------|
| 0 | Foundation | ✅ Complete | Manifesto, hypercube, global skills, verification protocol |
| 1 | Real WASM Codegen | 🔄 In Progress | let, if, calls, loops, return expressions |
| 2 | Knowledge → Codegen | ⏳ Planned | Algorithm suggestions change emitted WASM |
| 3 | Unified Glue | ⏳ Planned | wasm-bindgen for CLI and browser |
| 4 | Slim WASM | ⏳ Planned | Browser-minimal feature flag (< 100 KB) |
| 5 | Spec vs Impl | ⏳ Planned | Close `.frontier` spec / v2 parser gap |
| 6 | Self-Hosting | ⏳ Planned | Compile `frontier/core/*.frontier` natively |
| 7 | Neural LSP | ⏳ Planned | Production-grade completion via `src/neural/` |
| 8 | Decentralized Packages | ⏳ Planned | IPFS registry integration |
| 9 | Proof-Carrying Code | ⏳ Planned | Coq proofs attached to compiled artifacts |
| 10 | Universal Correlation | ⏳ Planned | `frontier foundation *` across all repos |

---

## Phase 1 — Real WASM Codegen (current)

File: `src/wasm_codegen.rs`

- [x] P1 let bindings in WASM codegen
- [x] P1 if/else branches
- [x] P1 function calls
- [x] P1 while loops
- [x] P1 return expressions
- [x] P1 `cargo test --lib wasm_codegen::` (6 tests)
- [ ] P1 knowledge hint changes emitted WASM (Phase 2 — post-release)
- [ ] P1 floats, strings, structs in WASM (post-release)

Phases 2–10 remain planned (not claimed complete).

## Current Priority

**Phase 1: Real WASM Codegen** — core constructs shipped; Phase 2 knowledge bridge next.

- File: `src/wasm_codegen.rs`
- Test: `cargo test --lib wasm_codegen`

---

## Verification Gates

Each phase must pass before the next begins:

```bash
.cursor/frontier_agent.sh true    # Core 5-component verification
.cursor/frontier_agent.sh gaps    # Honest gap report
python3 build/arc_orchestrator.py --verify
```
