# Architecture rationale — agent audit & ecosystem knowledge

Maps each design choice to authoritative 2024–2026 guidance (research, standards, OSS).

## 1. Append-only JSONL audit trail

**Choice:** `docs/agent_audit_log/sessions/YYYY-MM-DD.jsonl` — one JSON object per line, never edited in place.

**Backing:**
- **OpenTelemetry Logs Data Model** (CNCF, stable 1.x) — structured logs with severity, body, attributes; our `category`, `action`, `honesty` map to OTel log record fields.
- **NIST SP 800-92** (Guide to Computer Security Log Management) — append-only, centralized review, integrity protection.
- **W3C Trace Context** — `parent_id` field enables correlating agent tool chains.

## 2. Hash chain integrity (`prev_hash` + `entry_hash`)

**Choice:** Each entry SHA-256 hashes the prior entry hash.

**Backing:**
- **Sigstore Rekor** (OpenSSF) — transparency log pattern for tamper-evident records.
- **Merkle/hash-chain audit logs** — standard in certificate transparency (RFC 9162, 2021, still authoritative for chained logs).

## 3. PII separation (public SHA256 vs private prompt store)

**Choice:** `user_prompt_sha256` in committed logs; full text in gitignored `state/private_prompts.jsonl`.

**Backing:**
- **NIST AI RMF Generative AI Profile** (NIST AI 600-1, July 2024) — minimize sensitive data in operational logs; document data flows.
- **OWASP Top 10 for LLM Applications 2025** — logging for accountability without storing sensitive user content in shared repos.
- **GDPR Art. 5(1)(c)** — data minimization.

## 4. Ecosystem inventory via GitHub API (shallow scan)

**Choice:** `gh repo list` + README excerpt + top-level file probe; no clone/build of 27 repos per run.

**Backing:**
- **NTIA Minimum Elements for SBOM** (2021, US Dept. of Commerce) — supplier name, component name, version; our manifest maps repo → category → blueprint relation.
- **CycloneDX / SPDX** ecosystem — inventory before deep SBOM; shallow scan is Phase 0 inventory.

## 5. Blueprint phase gating (`TRACKING.json` + `tracking.py gate`)

**Choice:** No phase N+1 work until phase N validated with evidence.

**Backing:**
- **Internal:** `PROJECT_BLUEPRINT.md` — single source of truth for this repo.
- **External analog:** Google SRE launch checklist / progressive delivery — hard gates before expansion (Beyer et al., *Site Reliability Engineering*, O'Reilly).

## 6. Phase 6 LoRA deferral (not from-scratch LLM)

**Choice:** Fine-tune after Phase 1 exit; corpus gated on #44–#46 closed.

**Backing:**
- **LoRA** (Hu et al., 2021) — low-rank adaptation; still standard in 2025–2026 stacks.
- **Hugging Face PEFT / QLoRA docs** (2024–2025) — practical fine-tuning without full pretrain.
- **NIST AI RMF** — capability assessment before deploying generative components.

## 7. CI validation (`blueprint-gate.yml`)

**Choice:** Scrub → validate schema → unit tests → ecosystem dry-run on every PR touching audit paths.

**Backing:**
- **DORA metrics research** (Forsgren et al.) — automated gates reduce change failure rate.
- **OpenSSF Scorecard** — CI security checks as baseline supply-chain hygiene.

## 8. Performance SLAs (`manifest/ecosystem_gather_sla.json`)

**Choice:** ≤60 s total, ≤5 s/repo for metadata gather; `--fast` skips cargo for CI.

**Backing:**
- **SRE SLA/SLO/SLI framework** — explicit caps enable regression detection via `manifest/ecosystem_gather_benchmark.json`.

## References (URLs)

| ID | Resource |
|----|----------|
| R1 | https://opentelemetry.io/docs/specs/otel/logs/data-model/ |
| R2 | https://www.nist.gov/itl/ai-risk-management-framework |
| R3 | https://owasp.org/www-project-top-10-for-large-language-model-applications/ |
| R4 | https://www.ntia.gov/page/software-bill-materials |
| R5 | https://docs.sigstore.dev/logging/overview/ |
| R6 | https://huggingface.co/docs/peft |
