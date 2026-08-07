# Frontier Syntax — Enterprise Roadmap

**Version:** 1.0  
**Blueprint basis:** `PROJECT_BLUEPRINT.md` v2.0 (WASM primary)  
**Review gather:** `audit_reports/review_gather/` via `scripts/gather_for_review.sh`  
**Branch audited:** `cursor/blueprint-v2-wasm-llm-f519` @ `c5bcf21`  
**Generated:** 2026-08-06

This document is the forward-looking enterprise plan. It is grounded in **runtime verification**, not static claims. Where something was not executed, it is marked **unverified**.

---

## 1. What we actually ran (adapted gather)

The generic `/gather-for-review` command was **not** copied verbatim. The repo already has a practical adaptation:

```bash
bash scripts/gather_for_review.sh
# Output: audit_reports/review_gather/
```

### Adaptations vs generic command

| Generic command assumption | Frontier reality |
|---------------------------|----------------|
| `*.worker.*` files | **Zero found.** Workers are Python/shell orchestrators in `scripts/`, plus `frontier_agent.py`, `.cursor/symbiotic_agents.py` |
| `pie-extension/` | **Does not exist** |
| `.github/workflows/` | **Does not exist** — no CI |
| `cargo build --target wasm32` (all targets) | **Fails** — builds `lsp`/`lighthouse` bins without `serde_json` on wasm-slim path |
| Authoritative WASM build | `cargo build --lib --no-default-features --features wasm-slim` via `measure_wasm_size.py` |
| Gate truth | `python3 scripts/tracking.py gate` |
| Execution truth | `python3 scripts/verify_wasm_codegen.py` |

### Verified runtime results (this environment)

| Check | Result | Evidence |
|-------|--------|----------|
| `cargo build` (native) | **PASS** | `phase6_cargo_build.txt` exit 0 |
| `cargo test --lib` | **PASS** (40/40) | `phase6_cargo_test_lib.txt` |
| `verify_wasm_codegen.py` | **PASS** (4/4 wasmtime) | `phase6_verify_wasm_codegen.txt` |
| `measure_wasm_size.py` | **PASS** (83.8 KB, `met: true`) | `phase6_measure_wasm_size.txt` |
| `tracking.py gate` | **FAIL** | Phase 0 regressed — 10 open issues |
| `cargo clippy -D warnings` | **FAIL** | Unused imports, dead code |
| `cargo build --target wasm32` (full) | **FAIL** | Bin targets need serde_json; use wasm-slim lib build |

---

## 2. Critical blocker: tracker hygiene regressed

**Phase 0 is failing again.** Issues #59–#63 duplicate #44–#48.

```
Open: 44, 45, 46, 47, 48, 59, 60, 61, 62, 63  (10 total; expected 5)
```

Until dedupe is restored, **every gate downstream is blocked** — including Phase 1 evidence you already have. This is the highest-priority operational fix, before any new feature work.

**Slice 0.1 (re-run):** Close #59–#63 as duplicates of #44–#48; add pre-file guard to swarm scripts so they cannot re-open canonical issues.

---

## 3. Worker system — what actually exists

There is no `pie-extension`. The automation layer is:

### Tier A — Use for blueprint work (trusted)

| Component | Role | Invoke |
|-----------|------|--------|
| `scripts/tracking.py gate` | Phase gate, no partial credit | `python3 scripts/tracking.py gate` |
| `scripts/verify_wasm_codegen.py` | wasmtime execution oracle | `python3 scripts/verify_wasm_codegen.py` |
| `scripts/measure_wasm_size.py` | Authoritative WASM size | `python3 scripts/measure_wasm_size.py` |
| `scripts/blueprint_phase_swarm.py` | Sequential phases 0–3 only | `python3 scripts/blueprint_phase_swarm.py` |
| `scripts/gather_for_review.sh` | Review data package | `bash scripts/gather_for_review.sh` |

### Tier B — Useful but do not trust for gate closure

| Component | Risk |
|-----------|------|
| `frontier_agent.py` | Runs broad verification; can over-report success |
| `scripts/gap_solution_orchestrator.py` | **Always exits 0** even when gaps unsolved |
| `scripts/runtime_ipfs.py` | Offline fallback returns `pass: true` |
| `scripts/ultimate_conclusion_orchestrator.py` | Marks gaps resolved via file fallback |
| `scripts/parallel_scrub.py` | Runs each step **twice** (likely bug) |
| `scripts/deploy_lexicon_bound_swarm.py` | 23/24 workers pass on `--help`; not a gate |

### Tier C — Frozen until Phase 3 passes

All parallel all-phase swarms, `self_creation_orchestrator.py`, Phase 4–8 workers per `TRACKING.json`.

**Enterprise rule:** Only Tier A outputs may close blueprint slices. Everything else is exploratory signal.

---

## 4. Code review triage (21-pass analysis vs verified)

Static review findings were triaged against live code and execution.

### Confirmed bugs (fix before Phase 1 credibility)

| ID | Issue | Severity | Status |
|----|-------|----------|--------|
| B1 | `StringLiteral` / `FloatLiteral` silently emit `i32.const 0` | P0 | **Open** — should `Err(...)` |
| B2 | `export_section_static` resets `func_idx = 0` on `"main"` — breaks **browser** stub exports (`compile_wasm`, etc.) | P0 | **Open** for `--browser` path; non-browser OK after main-reorder fix |
| B3 | `validate_program_types()` is a no-op — missing `main` gives wrong error | P1 | **Open** |
| B4 | `ImportDecl` silently ignored in codegen | P1 | **Open** — should error |
| B5 | `RequiredExpr` error says "Field access" | P2 | **Open** |

### Confirmed gaps (not bugs, but enterprise debt)

| ID | Issue | Priority |
|----|-------|----------|
| G1 | `&&` / `\|\|` not short-circuiting | P2 — document or fix |
| G2 | Lexer runs twice in `compile_source` (profile path discards tokens) | P3 |
| G3 | Error messages lack line/column spans | P2 |
| G4 | No error-path unit tests in `wasm_codegen` | P1 |
| G5 | No CI (`.github/workflows` missing) | P0 for enterprise |
| G6 | `cargo clippy -D warnings` fails | P1 |
| G7 | Full `cargo build --target wasm32` builds wrong targets | P1 — document wasm-slim as canonical |

### Review claims corrected

| Claim | Verdict |
|-------|---------|
| `ark-*` / `pqcrypto-*` unused | **Wrong** — used in `src/zk/`, `src/pq_signatures.rs`; gated behind features |
| `reqwest` unused | **Wrong** — used in `src/ipfs/resolver.rs`; native-only |
| `main` export index bug | **Partially fixed** — function reorder helps default path; browser export table still broken |
| From-scratch LLM viable | **Rejected** — see `docs/phase6_synthetic_training_plan.md` |
| `pie-extension` workers | **Does not exist** |

---

## 5. Enterprise maturity model

```
Level 0 — Honest tracker     ← REGRESSED (10 issues; need 5)
Level 1 — Compiler executes   ← IN PROGRESS (wasmtime 4/4; #44 open)
Level 2 — Spec parity         ← BLOCKED
Level 3 — Size + CI           ← Size met; CI missing
Level 4 — Innovations earned  ← FROZEN
Level 5 — Self-hosting        ← FROZEN
Level 6 — Fine-tuned agent    ← PLANNED (corpus gated on Phase 1)
Level 7 — Production          ← FROZEN
```

**Current level: 0.5** — compiler evidence exists but tracker and independent validation do not support promotion.

---

## 6. Roadmap — phases and slices

Aligned with `PROJECT_BLUEPRINT.md` v2.0. **No parallel phase work.** Each slice has one verification command and one validator (not the implementer).

### Wave 1 — Restore truth (immediate)

| Slice | Action | Verification | Exit |
|-------|--------|--------------|------|
| 0.1-R | Close #59–#63 as dupes of #44–#48 | `gh issue list --state open` → exactly 5 | Phase 0.1 pass |
| 0.2-R | Add issue pre-file guard to `blueprint_phase_swarm.py`, `swarm_close_gaps.py`, `auto_fix_gaps.py` | Script refuses to file if canonical slug open | No new dupes in 7 days |
| 0.3-R | Pin gate commands in `LAUNCH_CHECKLIST.md` to Tier A scripts only | Manual read | No swarm script listed as gate |

### Wave 2 — Phase 1 compiler (WASM primary)

| Slice | Action | Verification |
|-------|--------|--------------|
| 1.1-a | Fix B1 (string/float → Err) | New negative tests + `verify_wasm_codegen.py` still 4/4 |
| 1.1-b | Fix B2 (browser export indices) | Test with `--browser` + wasmtime |
| 1.1-c | Add error-path tests (unknown var, unknown fn, bad types) | `cargo test --lib wasm_codegen::` |
| 1.1-d | Independent validator runs full 1.1 pipeline | Closes #44 |
| 1.2 | Knowledge → codegen (already has unit test) | Independent validator closes #45 |
| 1.3 | One Frontier-native self-hosted file | **Not bootstrap** — closes #46 |

**Phase 1 exit:** `tracking.py gate` → `phase_1_pass: true`

### Wave 3 — Engineering hygiene (parallel to 1.x, does not gate Phase 1)

| Slice | Action |
|-------|--------|
| HY-1 | `.github/workflows/gate.yml` — run Tier A on every PR |
| HY-2 | `cargo clippy` clean or scoped allowlist with ticket refs |
| HY-3 | Document canonical WASM build: `--no-default-features --features wasm-slim` |
| HY-4 | Fix `gather_for_review.sh` phase 7 hang (workers without `--help`) |

### Wave 4 — Phase 2–3 (after Phase 1)

| Phase | Key deliverable |
|-------|-----------------|
| 2.1 | `spec_impl_bridge.py` semantic parity, not file existence — closes #47 |
| 2.2 | Edge-case tests (overflow, deep nest, malformed input) |
| 3.1 | WASM size issue #48 closed by validator (measurement already `met: true`) |

### Wave 5 — Phase 6 LLM (corpus after Phase 1 only)

See `docs/phase6_synthetic_training_plan.md`:

1. **6.1** Generate synthetic corpus (≥1k samples, 100% compile, wasmtime-validated)
2. **6.2** LoRA fine-tune 1–7B open code model ($50–300 envelope)
3. **6.3** Agent runtime with WASM sandbox only (after Phase 5)

**Do not spend GPU until Phase 1 exit.** Compiler semantics are the label oracle.

### Wave 6 — Phases 4–5–7–8 (frozen until prior gates pass)

No work. Innovations, self-hosting expansion, production hardening, launch remain frozen per blueprint.

---

## 7. CI blueprint (minimal enterprise gate)

Proposed `.github/workflows/blueprint-gate.yml`:

```yaml
name: Blueprint Gate
on: [push, pull_request]
jobs:
  gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with:
          targets: wasm32-unknown-unknown
      - run: cargo test --lib
      - run: python3 scripts/verify_wasm_codegen.py
      - run: python3 scripts/measure_wasm_size.py
      - run: python3 scripts/tracking.py gate
```

**Do not** wire Tier B swarms into CI until they have honest exit codes.

---

## 8. Definition of enterprise-ready

The project reaches enterprise-grade **for the compiler MVP** when:

1. `tracking.py gate` exits 0 through Phase 3
2. CI runs Tier A on every PR
3. Issues #44–#48 closed by independent validator (not self-validation swarms)
4. `verify_wasm_codegen.py` includes error-path cases (must fail correctly)
5. WASM build documented and reproducible from one command
6. Synthetic training corpus (6.1) generated only after Phase 1 exit
7. No duplicate issues re-filed for 30 days

---

## 9. Immediate next actions (ordered)

1. **Re-dedupe issues** #59–#63 → restore Phase 0
2. **Fix B1** (silent string/float) + add negative tests
3. **Fix B2** (browser export indices) if `--browser` is in scope for Phase 1
4. **Add CI** with Tier A gate scripts
5. **Independent validator** runs 1.1 pipeline → close #44
6. **Do not** run corpus generation or GPU fine-tune until step 5 completes

---

## 10. Artifacts for human review

| Artifact | Path |
|----------|------|
| Full gather package | `audit_reports/review_gather/full_review_package.md` (if phase 10 completed) |
| Summary | `audit_reports/review_gather/summary.md` |
| Worker catalog | `audit_reports/review_gather/phase3_workers.txt` (72 scripts) |
| Key modules | `audit_reports/review_gather/phase2_key_modules_full.txt` |
| Gate output | `audit_reports/review_gather/phase6_tracking_gate.txt` |
| Blueprint v2.0 | `PROJECT_BLUEPRINT.md` |
| LLM corpus plan | `docs/phase6_synthetic_training_plan.md` |

---

*This roadmap supersedes informal swarm reports and README claims. If a document disagrees with `tracking.py gate` output, the gate wins.*
