# FROZEN — DO NOT IMPLEMENT

> **This spec was created prematurely during a parallel all-phase swarm run.**
> Per PROJECT_BLUEPRINT.md v2.0:
> - **Slice 6.1 (corpus):** blocked until **Phase 1** passes (#44–#46 closed).
> - **Slice 6.2–6.3 (fine-tune + agent runtime):** blocked until **Phase 5** passes.
> - Phase 4 is blocked until Phase 3 passes (WASM size criterion met; issue #48 must still close).
>
> No agent work may proceed from this document until the relevant gate passes.

# Phase 6 Agent Spec (Blueprint prerequisite — NOT ACTIVE)

## Status: FROZEN / INVALIDATED

## Compilation target (v2.0 policy)

- **Primary execution path:** WASM (`src/wasm_codegen.rs`) + wasmtime
- **Native:** optional/deferred; not the agent sandbox v1
- Agent-generated code is validated with the same pipeline as `scripts/verify_wasm_codegen.py`

## LLM strategy (decision record)

| Approach | Verdict |
|----------|---------|
| From-scratch pretrain | **Rejected** — no corpus, six-to-seven-figure compute |
| Synthetic pretrain on moving compiler | **Rejected** — P0 fixes invalidate labels |
| **LoRA fine-tune on validated synthetic corpus** | **Selected** — solo-buildable, tens–low hundreds USD |

**Corpus plan:** `docs/phase6_synthetic_training_plan.md`

## What the agent would need to answer (when unfrozen)
- What can the agent do that a human + Frontier compiler cannot? (concrete 10x claim)
- What is out of scope for v1?
- What is the sandboxing/safety boundary?

## Safety boundary (draft only — not approved)
- All actions logged to `docs/lexicon_log.fr`
- Lexicon Hard Gate requires documentation
- Intents routed through `frontier_agent.py`
- **Execution:** wasmtime only in v1 — no native shell, no `--bootstrap` in agent loop
- Generated code must pass compile + wasmtime before any merge proposal
