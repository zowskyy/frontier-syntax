# PROJECT_BLUEPRINT.md — Frontier Syntax → Production
**Repo:** zowskyy/frontier-syntax
**Blueprint version:** 2.0 (supersedes v1.0; WASM reaffirmed as primary compilation target)
**Basis:** Live audit of README, LAUNCH_CHECKLIST.md, open issues #35–#48, and gate evidence in `manifest/` — not the repo's self-reported status.
**Rule:** This document is the single source of truth. If code, README, or a script disagrees with this file, this file wins until updated with evidence.

---

## 0. Compilation target policy (v2.0)

| Target | Status | Canonical path | Notes |
|--------|--------|----------------|-------|
| **WASM** | **Primary** | `src/wasm_codegen.rs` → `frontier compile -t wasm` | Execution verified via `wasmtime` (`scripts/verify_wasm_codegen.py`). Slim browser build measured in `manifest/wasm_size.json`. |
| **Native** | Optional / deferred | `frontier compile --bootstrap` (Rust wrapper) | Not a Phase 1–3 gate criterion. True Frontier-native codegen is Phase 5 exit, not a prerequisite for WASM correctness or the Phase 6 LLM. |

**Implication:** All acceptance criteria for “does the program run?” mean **compile to WASM and execute in wasmtime** unless a slice explicitly says otherwise. Do not block WASM work on native bootstrap progress.

---

## 0. Ground Truth (what is actually verified vs. claimed)

| Claim in repo | Verified status |
|---|---|
| "All 6 cycles complete," "All tests passing," LAUNCH_CHECKLIST all technical boxes checked | **Unverified.** Contradicted by open P0 issues on the same functionality. |
| WASM codegen: let/if/calls/loops supported | **Partially verified, not closed.** Unit tests + `scripts/verify_wasm_codegen.py` (wasmtime wast, 4/4) pass; issue #44 still open — no independent validator closure. |
| Knowledge → codegen wiring | **Tests pass, not closed.** `test_knowledge_changes_wasm` passes; issue #45 still open. |
| Genesis self-hosting bootstrap | **False.** Issue #46 (P0): `.frontier` spec files are not valid v2 source. 0% self-hosting. |
| WASM binary size | **Target met (measurement).** `manifest/wasm_size.json`: 83.8 KB (`met: true`); issue #48 still open until validator closes. |
| Spec/impl parity for core modules | **Gap confirmed.** Issue #47/#40/#35 (P1). |
| Issue tracker itself | **Unreliable.** Issues #35–48 are 4 duplicate filings of the same 5 root problems — the swarm re-discovers and re-files instead of closing. No independent validator has ever closed a P0. |

**Conclusion:** the compiler cannot execute a program with control flow. Every "innovation" (ZK verifier, PQ signatures, neural LSP, IPFS resolver, self-mutating grammar) sits on top of a core that doesn't work yet. Nothing past Phase 3 below is real until Phase 1 is.

---

## 1. Non-negotiable rules for this roadmap (from your own AEF contract)

- No new feature work while any P0 is open.
- No slice is `MERGED` without a validator that is **not** the implementer running the actual verification command and recording output.
- No document (README, ANNOUNCEMENT, FINAL_CERTIFICATION, LAUNCH_CHECKLIST) may claim a status the tracking gate doesn't support. If a claim can't currently be backed, mark it `NOT VERIFIED`, not remove it silently.
- `docs/process_log.fr` must log failures and re-openings, not just successes — that log is currently one-sided, which is how the same 5 bugs got filed 4 times without anyone noticing they were never fixed.

---

## 2. Phase 0 — Tracker & Truth Hygiene
*Goal: stop lying to yourself before writing more code. 1 day.*

**SLICE 0.1 — Deduplicate issue tracker**
- Root cause: swarm scripts file new issues instead of checking for existing open ones with the same root cause ID.
- Fix: close #35, #36, #37, #38, #39, #40, #41 as duplicates of #44/#45/#46/#47/#48; add a pre-file check (`grep` open issues by root-cause slug) to whichever script files issues.
- Verify: `gh issue list --state open` shows exactly 5 open issues, one per root cause.
- Status: NOT_STARTED

**SLICE 0.2 — Build the real gate**
- Create `TRACKING.json` seeded from the 5 canonical issues above, each with `acceptance_criteria[]`, `verification_command`, `status: not_started`.
- Create/fix `scripts/tracking.py gate` so it exits non-zero while any P0 lacks `validated` + evidence.
- Verify: `python3 scripts/tracking.py gate` currently exits non-zero (this is expected and correct right now).
- Status: NOT_STARTED

**SLICE 0.3 — Correct the public claims**
- Edit README "What's New" table, LAUNCH_CHECKLIST.md, FINAL_CERTIFICATION_v2.md: replace checked boxes for anything tied to #44/#45/#46 with `NOT VERIFIED — see issue #NN`.
- Verify: manual read-through, no `[x]` next to anything the gate script disputes.
- Status: NOT_STARTED

---

## 3. Phase 1 — Core Compiler Correctness (P0, blocking everything)
*Goal: the language can actually run a program. This is the real MVP. No estimate given — exit condition is validation, not a date.*

**SLICE 1.1 — WASM codegen: let/if/calls/loops** (closes #44)
- File: `src/wasm_codegen.rs`
- Acceptance criteria (each independently executable):
  1. `let x = 5; x + 1` compiles and evaluates to 6.
  2. `if` with both branches compiles and both branches are reachable/tested.
  3. A user-defined function call compiles and returns the correct value.
  4. A `while`/`for` loop compiles and terminates with the correct accumulated result.
- Verification: `cargo test --lib wasm_codegen::` **and** `python3 scripts/verify_wasm_codegen.py` (wasmtime wast execution, not compile-only).
- Validator: someone/something other than the agent that wrote the codegen must run step above from a clean checkout.

**SLICE 1.2 — Wire knowledge suggestions into codegen** (closes #45)
- File: `implementation_hint` handling path into `wasm_codegen.rs`.
- Acceptance: a known knowledge-base suggestion (e.g. a specific optimization or safety rewrite) measurably changes emitted WASM bytecode, not just a log line.
- Verification: diff WASM output with the knowledge hint enabled vs. disabled — diff must be non-empty and semantically correct.

**SLICE 1.3 — One real self-hosted file** (closes #46)
- Goal is not "0% → 100%" in one slice — goal is 0% → **1 real file**, verified.
- Pick the smallest module in `frontier/src/main.fr`. Make it valid v2 Frontier source that the *Frontier compiler itself* (not the Rust wrapper) parses and compiles correctly.
- Verification: `python3 scripts/verify_self_hosting.py` reports that specific file as passing with real compiler output, not the bootstrap wrapper.

**Phase 1 exit condition:** `scripts/tracking.py gate` passes for all 3 P0s, with logged evidence (command + output) for each, from a validator run.

---

## 4. Phase 2 — Core Language & Spec Parity (P1)
*Blocked until Phase 1 gate passes.*

**SLICE 2.1 — Close spec/impl gap** (closes #47)
- Enumerate every `.frontier` core module claim in `syntax/feature_matrix_v2.json` against `frontier/core/`. For each mismatch: either implement it or downgrade the spec to match reality — no third option.
- Verification: `python3 scripts/verify_language_hardening.py` — all 10 core modules pass against the corrected spec.

**SLICE 2.2 — Edge-case test coverage**
- `cargo test --lib` currently exists but scope is unknown — audit what it actually covers.
- Add tests for: empty input, deeply nested expressions, malformed but non-crashing input, integer overflow, recursion depth limits.
- Verification: `cargo test --lib -- --nocapture`, coverage report attached to PROJECT_STATE.md.

---

## 5. Phase 3 — Size & Performance Hardening (P1)
*Blocked until Phase 2 gate passes.*

**SLICE 3.1 — WASM binary size** (closes #48/#41/#36)
- Root cause hypothesis to confirm first: are the 7 "innovations" (ZK, PQ, IPFS, neural LSP) compiled into the core runtime path even when unused? If yes, feature-gate them out of the default build.
- Actions: `wasm-opt -Oz`, strip debug symbols, split innovations into optional crates behind Cargo features.
- Acceptance: default WASM build <100 KB, measured, not estimated.
- Verification: `manifest/wasm_size.json` regenerated and checked into the gate.

---

## 6. Phase 4 — Verification Claims Made Real (proofs, ZK, PQ)
*Blocked until Phase 3 gate passes. This is where the "7 innovations" get re-earned, not assumed.*

For **each** of: self-mutating grammar, proof-carrying code, PQ signatures, ZK-SNARK AST verification, IPFS imports, neural LSP, decentralized package registry:
- Write one acceptance criterion that is empirically checkable against the *now-working* compiler from Phase 1–3 (not against a hypothetical one).
- Independently validate. Anything that doesn't survive contact with a real program gets marked `SCOPED OUT (post-v2.1)` in this document — not deleted, not silently claimed.

---

## 7. Phase 5 — True Self-Hosting
*Blocked until Phase 4 gate passes.*

- Extend Slice 1.3's single-file proof to the full `frontier/src/main.fr` compiler.
- Exit condition: the Rust `--bootstrap` wrapper becomes optional, not required — the Frontier-native compiler can compile itself end to end.
- Verification: `python3 scripts/verify_self_hosting.py` on the full compiler, zero fallback to the Rust path.

---

## 8. Phase 6 — Independent AI Agent on Its Own Coding System
*Blocked until Phase 5 gate passes for **agent runtime and deployment**. Corpus generation (Slice 6.1) is additionally gated on Phase 1 exit — see below.*

### Why not “train a Frontier LLM from scratch” (decision record)

| Approach | Solo-founder viability | Blocker |
|----------|------------------------|---------|
| **From-scratch pretrain** | Not viable | Competent code models need hundreds of billions to trillions of tokens and low-to-mid six figures in compute minimum (seven figures for genuinely capable). |
| **Corpus scarcity** | Hard blocker (not budget) | Frontier has ~0 real-world programs. No GitHub corpus exists. You cannot pretrain on a language nobody has written yet. |
| **Synthetic pretrain now** | Wasted work | Compiler semantics still moving (#44 open; P0 fixes invalidate training labels). |
| **LoRA fine-tune (1–7B open code model)** | **Buildable solo** | Tens to low hundreds of USD GPU rental, days not months. Gets correct Frontier **syntax** for a Phase 6 coding agent. |

**Hard dependency (both paths):** training data quality = compiler ground truth. Generate the synthetic corpus **after** issues #44, #45, and #46 close so labels match settled semantics.

Before writing agent runtime code, produce a plain-language spec (per your own Phase 1 architecture rule) answering:
- What can the agent do that a human + the Frontier compiler couldn't? (the 10x claim, stated concretely)
- What is explicitly out of scope for v1 of this agent?
- What is the sandboxing/safety boundary for an agent that can write and execute its own code? (This needs its own security-gate pass — self-modifying, self-executing agents are exactly the "dangerous execution" and "prompt/tool injection" categories your Phase 3 security gate already flags.)

**SLICE 6.1 — Synthetic Frontier training corpus** (prep work; **gated on Phase 1 exit**)
- **Do not start** until `scripts/tracking.py gate` reports `phase_1_pass: true` (issues #44, #45, #46 closed by independent validator).
- **Input sources:** `syntax/feature_matrix_v2.json`, `frontier/docs/language_reference.md`, `examples/*.fr`, `cargo test --lib wasm_codegen::` cases, `scripts/verify_wasm_codegen.py` cases, passing `spec_impl_bridge` fixtures (post Phase 2).
- **Generation:** template + mutation scripts emit `.fr` snippets; each sample validated by compile → wasmtime execution (same pipeline as Slice 1.1).
- **Output:** `manifest/training_corpus/` (JSONL: `prompt`, `completion`, `source_spec`, `wasmtime_pass`, `git_sha`).
- **Verification:** ≥1,000 samples; 100% compile; ≥95% wasmtime pass on generated `main()` programs; zero samples from pre-Phase-1 compiler SHA.
- **Full plan:** `docs/phase6_synthetic_training_plan.md`

**SLICE 6.2 — LoRA fine-tune** (gated on 6.1 corpus validated)
- Base model: open code model in 1–7B class (e.g. StarCoder2-3B, CodeLlama-7B, Qwen2.5-Coder-3B).
- Method: LoRA/QLoRA on completion pairs from 6.1; no full pretrain.
- Acceptance: held-out Frontier syntax benchmark ≥90% parse+compile; human spot-check 20 samples.
- Budget envelope: document actual GPU cost; target tens–low hundreds USD.

**SLICE 6.3 — Agent runtime** (gated on Phase 5 + 6.2)
- Wire fine-tuned model into agent loop with WASM sandbox execution only (wasmtime, not native shell).
- All generated code must pass `verify_wasm_codegen.py`-equivalent pipeline before merge proposals.

Only after Slice 6.1 spec is validated on paper and Phase 5 passes do you scope remaining Salami slices for deployment. Scoping agent runtime on top of an unverified compiler is how you get five more duplicate P0 issues in a month.

---

## 9. Phase 7 — Production Hardening

- Live GPU/IPFS/CDX nodes: currently "external" per README — get one real deployment, not a module test, before claiming production readiness.
- CI: every gate in this document running automatically on PR, not just locally.
- Re-run the full Phase-3-style security gate (secrets, unsafe exec, deserialization, SSRF, injection) against the agent layer specifically — it's new attack surface.

---

## 10. Phase 8 — Launch
*This phase was already honestly scoped in LAUNCH_CHECKLIST.md — keep it, it's correct:*
- [ ] Website live (frontier.dev)
- [ ] Social media ready
- [ ] Waiting list active
- [ ] Launch date confirmed
- [ ] Discord server

Nothing above changes — these were already correctly marked incomplete. Don't touch them until Phase 7 is done.

---

## 11. Definition of Done (whole project)

The project is complete when `python3 scripts/tracking.py gate` exits 0 for **every** phase above, each item carrying a validator's logged command output — not a script's self-report, not a "swarm consensus," not a re-filed issue that was never closed. Two runs of the same gate, one week apart with no code change, should produce identical results — if they don't, the gate itself is untrustworthy and that's a P0.

---

## Review pass notes
This blueprint was drafted and then checked four times against the same failure mode your own AEF contract warns about — claiming completion the evidence doesn't support:
1. First pass — cross-checked every phase claim against the actual open issues (#35–48), not the README's self-reported status.
2. Second pass — removed anything phrased as already working; reworded to explicit acceptance criteria with a real verification command per slice.
3. Third pass — enforced dependency ordering so Phase 6 (the AI agent) can't be scoped or started before Phases 1–5 gate, since that's the exact ordering mistake visible in the current repo (innovations before working codegen).
4. Fourth pass — added the tracker-hygiene phase (0) as a prerequisite, since the duplicate-issue pattern means the project's own measurement system is currently unreliable and would silently re-certify false completion if not fixed first.

No slice above is marked done. That's intentional — this file has zero authority to mark anything validated; only your gate script and a real validator run can do that.
