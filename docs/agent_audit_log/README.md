# Agent audit log — in-repo record of every agent action + repo snapshots

<!-- SHADOW_WORKER_STATUS:BEGIN -->

_Auto-updated by `scripts/agent_shadow_worker.py` — 2026-08-07 02:51:01 UTC_

## Live status

| Signal | Value |
|--------|-------|
| Last agent activity | `2026-08-07T01:16:23.339410Z` |
| Session entries (index) | 83 |
| Latest repo snapshot | `20260806T181935Z` |
| Latest ecosystem run | `20260806T232938Z` |
| Ecosystem repos scanned | 27 |
| Ecosystem gather time | 13.083183411996288s (SLA met: True) |
| WASM size | 84.3 KB (target met: True) |
| Blueprint Phase 0 | ? |
| Blueprint Phase 1 | ? |
| Open issues | — |

**Shadow worker (run every turn / cron):**

```bash
python3 scripts/agent_shadow_worker.py run    # heartbeat + README refresh
python3 scripts/agent_shadow_worker.py run --ecosystem --snapshot  # full refresh
python3 scripts/agent_shadow_worker.py install-cron
```

<!-- SHADOW_WORKER_STATUS:END -->

## Where everything lives

| What | Path |
|------|------|
| **Every action log** (JSONL, one line per action) | `docs/agent_audit_log/sessions/YYYY-MM-DD.jsonl` |
| **Full repo review** (frontier-syntax deep gather) | `docs/agent_audit_log/repo_snapshots/<timestamp>/` |
| **Latest snapshot id** | `docs/agent_audit_log/repo_snapshots/LATEST.txt` |
| **Multi-repo ecosystem report** | `docs/agent_audit_log/ecosystem_knowledge/ECOSYSTEM_KNOWLEDGE_REPORT.txt` |
| **Ecosystem manifest** | `docs/agent_audit_log/ecosystem_knowledge/manifest.json` |
| **Latest ecosystem run id** | `docs/agent_audit_log/ecosystem_knowledge/LATEST.txt` |
| **Pipeline step logs** (per gather run) | `docs/agent_audit_log/pipeline_logs/<run_id>/pipeline.log` |
| **Index** | `docs/agent_audit_log/index.json` |

## Category layout

```
docs/agent_audit_log/
  sessions/              # every agent action (JSONL)
  repo_snapshots/        # frontier-syntax deep gather (structure, source, builds)
  ecosystem_knowledge/   # all zowskyy repos — claims vs verified vs blueprint
  pipeline_logs/         # per-run step logs for gather pipelines
  state/                 # local-only activity pointer (gitignored)
```

## Read the ecosystem report

```bash
# Latest consolidated multi-repo knowledge
cat docs/agent_audit_log/ecosystem_knowledge/ECOSYSTEM_KNOWLEDGE_REPORT.txt

# Machine-readable index
cat docs/agent_audit_log/ecosystem_knowledge/manifest.json

# Pipeline steps for the latest ecosystem run
RUN=$(cat docs/agent_audit_log/ecosystem_knowledge/LATEST.txt)
cat docs/agent_audit_log/pipeline_logs/$RUN/pipeline.log
```

## Regenerate ecosystem knowledge

```bash
python3 scripts/gather_ecosystem_knowledge.py
```

Every step is logged to `sessions/` and `pipeline_logs/<run_id>/`.

## Read the frontier-syntax repo dump

```bash
# Latest snapshot folder name
cat docs/agent_audit_log/repo_snapshots/LATEST.txt

# Table of contents
cat docs/agent_audit_log/repo_snapshots/$(cat docs/agent_audit_log/repo_snapshots/LATEST.txt)/full_review_package.md

# Full Rust key modules
cat docs/agent_audit_log/repo_snapshots/$(cat docs/agent_audit_log/repo_snapshots/LATEST.txt)/phase2_key_modules_full.txt

# All workers/scripts
cat docs/agent_audit_log/repo_snapshots/$(cat docs/agent_audit_log/repo_snapshots/LATEST.txt)/phase3_workers.txt
```

## Regenerate repo snapshot

```bash
bash scripts/gather_for_review.sh
# or
python3 scripts/agent_shadow_worker.py run --snapshot
```

## Log an action (agents: every tool call)

```bash
python3 scripts/agent_audit_hook.py --tool Shell --action "cargo test" --command "cargo test --lib" --exit 0 --verified
```

## Policy

- **Every action** is logged — no "significant only" filter.
- Secrets redacted automatically (`ghp_*`, tokens, etc.).
- **PII policy:** see `DATA_CLASSIFICATION.md` — prompts never in committed sessions.
- **Architecture:** see `ARCHITECTURE_RATIONALE.md` for research citations.
- `state/` is local-only (gitignored); `sessions/`, `repo_snapshots/`, `ecosystem_knowledge/`, and `pipeline_logs/` are committed for your review.

## Validate & scrub

```bash
python3 scripts/scrub_audit_sessions.py      # idempotent PII scrub + hash chain
python3 scripts/validate_audit_log.py --strict-hash
```
