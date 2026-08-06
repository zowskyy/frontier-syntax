# FROZEN — DO NOT IMPLEMENT

> **This spec was created prematurely during a parallel all-phase swarm run.**
> Per PROJECT_BLUEPRINT.md: Phase 6 is **blocked until Phase 5 passes**.
> Phase 5 is **blocked until Phase 4 passes**.
> Phase 4 is **blocked until Phase 3 passes** (WASM size <100 KB).
>
> No agent work may proceed from this document until `python3 scripts/tracking.py gate` reports `phase_3_pass: true`.

# Phase 6 Agent Spec (Blueprint prerequisite — NOT ACTIVE)

## Status: FROZEN / INVALIDATED

## What the agent would need to answer (when unfrozen)
- What can the agent do that a human + Frontier compiler cannot? (concrete 10x claim)
- What is out of scope for v1?
- What is the sandboxing/safety boundary?

## Safety boundary (draft only — not approved)
- All actions logged to docs/lexicon_log.fr
- Lexicon Hard Gate requires documentation
- Intents routed through frontier_agent.py
