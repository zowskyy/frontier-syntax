# Phase 6 — Synthetic Frontier Training Corpus (Slice 6.1)

> **Status:** PLANNED — **FROZEN until Phase 1 gate passes**
>
> Do not generate or commit training data until `scripts/tracking.py gate` reports
> `phase_1_pass: true` (issues #44, #45, #46 closed by an independent validator).
> Generating now wastes work: every P0 semantics fix invalidates labels.

**Blueprint ref:** `PROJECT_BLUEPRINT.md` §8, Slice 6.1  
**Compilation ground truth:** WASM via `src/wasm_codegen.rs`, executed with wasmtime  
**Agent spec (runtime):** `docs/blueprint_phase6_agent_spec.md` — still frozen until Phase 5

---

## 1. Goal

Produce a **private, correct, Frontier-specific** dataset to LoRA fine-tune an existing open code model (1–7B class). This is **not** from-scratch pretraining.

**Success:** a model that writes syntactically valid Frontier v2 and produces programs that compile and run under the **current** compiler — not yesterday's broken semantics.

---

## 2. Why not from scratch (numbers)

| Item | Order of magnitude |
|------|-------------------|
| Competent code-model pretrain tokens | 10²–10³ **billion** tokens |
| StarCoder-class training cost | Low-to-mid **six figures** USD compute minimum |
| Genuinely capable from-scratch | **Seven figures** USD |
| Real-world Frontier corpus on GitHub | **~0** repos |
| LoRA fine-tune on synthetic corpus | **Tens–low hundreds** USD; **days**; **one person** |

**Corpus scarcity is the hard blocker**, not grit. No amount of solo work invents a pretraining corpus for a language nobody has shipped in production.

---

## 3. Hard dependencies

```
Phase 1 exit (#44, #45, #46 closed)
        │
        ▼
Slice 6.1 — generate + validate corpus  ◄── YOU ARE HERE (plan only)
        │
        ▼
Slice 6.2 — LoRA fine-tune
        │
        ▼
Phase 5 exit (Frontier-native self-host)
        │
        ▼
Slice 6.3 — agent runtime (WASM sandbox)
```

**Compiler = label oracle.** Every training sample must pass:

```bash
cargo test --lib wasm_codegen::
python3 scripts/verify_wasm_codegen.py   # wasmtime wast assert_return
```

If a P0 fix lands after corpus generation, **regenerate** affected shards (pin `git_sha` per sample).

---

## 4. Input sources (ground truth)

| Source | Use |
|--------|-----|
| `syntax/feature_matrix_v2.json` | Feature coverage matrix — one prompt template per feature |
| `syntax/Frontier.g4`, `syntax/schema_v2.json` | AST shape constraints |
| `frontier/docs/language_reference.md` | Human-readable syntax (curate; doc may lag spec) |
| `examples/*.fr`, `examples/v2_parser_test.fr` | Seed programs |
| `scripts/verify_wasm_codegen.py` `CASES` | Executable oracles (extend as codegen grows) |
| `cargo test --lib wasm_codegen::` | Unit-test oracles |
| `manifest/spec_impl_bridge.json` (post Phase 2) | Spec/impl alignment fixtures |

**Exclude:** `docs/process_log.fr`, chat scrub, swarm logs — noisy, not validated against wasmtime.

---

## 5. Generation pipeline

### 5.1 Script layout (to implement after Phase 1)

```
scripts/training/
  generate_corpus.py      # template expansion + mutation
  validate_sample.py      # compile → wasmtime per sample
  export_jsonl.py         # shard writer
```

### 5.2 Sample types (priority order)

1. **Syntax completion** — partial program → complete `fn main(): int { ... }`
2. **Feature isolation** — one construct per sample (`let`, `if/else`, `while`, calls)
3. **Bug fix** — broken Frontier snippet → fixed snippet (both sides validated)
4. **Spec-to-code** — natural language from feature matrix → Frontier program
5. **Test synthesis** — given behavior description → program + expected return value

### 5.3 Validation gate (per sample)

```python
# Pseudocode — every sample must pass before inclusion
source = sample["completion"]
compile(source, "-t", "wasm", "--no-optimize")  # must exit 0
wasmtime_wast_assert_return(wasm, sample["expected"])  # must pass
```

Record failures to `manifest/training_corpus/rejects.jsonl` with reason — never silently drop.

### 5.4 Output format

`manifest/training_corpus/frontier_v1.jsonl` (one JSON object per line):

```json
{
  "id": "let_if_0042",
  "prompt": "Write a Frontier function main that returns 10 when x > 5...",
  "completion": "fn main(): int { let x: int = 10; if (x > 5) { return x; } return 0; }",
  "expected_return": 10,
  "features": ["let", "if", "relational"],
  "source_spec": "syntax/feature_matrix_v2.json#control_flow",
  "compiler_git_sha": "d426b2b",
  "wasmtime_pass": true,
  "generated_at": "2026-08-06T00:00:00Z"
}
```

Train/val/test split: 80/10/10 by **feature tag**, not random line — avoid leakage.

---

## 6. Volume targets (v1)

| Metric | Target |
|--------|--------|
| Total samples | ≥ 1,000 (v1); scale to 10k after assignment/loop semantics settle |
| Compile pass rate | 100% (reject at generation time) |
| wasmtime pass rate | ≥ 95% on samples with `expected_return` |
| Unique feature tags | Cover all Phase 1 constructs before Phase 2 features |
| Max sample length | 512 tokens completion (fits 1–7B context with prompt) |

---

## 7. LoRA fine-tune (Slice 6.2 — outline only)

| Parameter | Recommendation |
|-----------|----------------|
| Base model | Open code model 1–7B (StarCoder2-3B, Qwen2.5-Coder-3B, or CodeLlama-7B) |
| Method | QLoRA, rank 16–64, 1–3 epochs |
| Hardware | Single A10/L4 or 4090 rental |
| Cost envelope | $50–300 USD |
| Eval | Held-out `verify_wasm_codegen.py` cases + 20 human spot-checks |

**Do not start 6.2 until 6.1 manifest exists and `validate_corpus.py` passes on full shard.**

---

## 8. What this does *not* solve

- **Semantic depth** beyond what the compiler validates (no types beyond i32 MVP yet)
- **Natural-language agent safety** — Slice 6.3 sandbox still required
- **Self-hosting** — Phase 5; model does not replace `frontier/src/main.fr`
- **From-scratch Frontier tokenizer** — use base model tokenizer; Frontier is ASCII-friendly

---

## 9. Exit criteria (Slice 6.1)

- [ ] `phase_1_pass: true` in tracking gate
- [ ] `scripts/training/generate_corpus.py` exists and is deterministic given seed
- [ ] `manifest/training_corpus/frontier_v1.jsonl` committed with ≥1,000 validated samples
- [ ] `manifest/training_corpus/stats.json` — pass rates, feature coverage, compiler SHA
- [ ] Independent validator runs `validate_corpus.py` on clean checkout and confirms stats

**Until all boxes checked:** this document is plan-only; no GPU spend, no corpus commits.
