# Data classification — agent audit log

## Public (committed to git)

| Path | Classification | May contain |
|------|----------------|-------------|
| `sessions/*.jsonl` | **Internal — public repo** | Agent actions, commands, git metadata, SHA256 of prompts |
| `ecosystem_knowledge/` | **Internal** | Upstream README excerpts (inventory only) |
| `pipeline_logs/` | **Internal** | Pipeline step metadata, per-repo JSON profiles |
| `repo_snapshots/` | **Internal** | Source tree, build output excerpts |

### MUST NOT appear in committed files

- Raw `user_prompt_excerpt` (use `user_prompt_sha256` only)
- API tokens, passwords, private keys (`ghp_*`, etc.)
- Email addresses, personal legal statements (full text)
- Private repo source content

## Private (gitignored — `state/`)

| Path | Classification |
|------|----------------|
| `state/private_prompts.jsonl` | **Confidential** — full user prompt excerpts |
| `state/activity.json` | **Internal** — last activity pointer |
| `state/shadow_worker.log` | **Internal** |

## GDPR / retention

- **Lawful basis:** Legitimate interest (engineering audit trail) — document in your privacy policy.
- **Retention:** Default 90 days for session export (`scripts/audit_log_retention.py export-old`).
- **Erasure (DSAR):** Run retention export, then `git filter-repo` or revert commits containing the subject's `entry_id`. Private prompts in `state/` can be deleted locally without git history rewrite.
- **Data minimization:** Prompts stored as SHA256 in public log; full text only in gitignored `state/`.

## SOC2 controls (target)

| Control | Implementation |
|---------|----------------|
| Integrity | SHA-256 hash chain (`prev_hash`, `entry_hash`) |
| Validation | `scripts/validate_audit_log.py` in CI |
| Access | GitHub branch protection on `main`; private prompts local-only |
| Monitoring | `pipeline.log` + CI `blueprint-gate.yml` |
