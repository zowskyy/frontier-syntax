# Agent Audit Log — mandatory (every action)

Log **every** tool call and response turn. No exceptions.

```bash
python3 scripts/agent_audit_hook.py \
  --tool <Shell|Read|Grep|Write|...> \
  --action "<what>" \
  --command "<exact command or path>" \
  --exit-code <code> \
  --verified
```

## Locations

- Actions: `docs/agent_audit_log/sessions/YYYY-MM-DD.jsonl`
- Repo dump: `docs/agent_audit_log/repo_snapshots/` (see `LATEST.txt`)
- Ecosystem report: `docs/agent_audit_log/ecosystem_knowledge/ECOSYSTEM_KNOWLEDGE_REPORT.txt`
- Pipeline logs: `docs/agent_audit_log/pipeline_logs/<run_id>/pipeline.log`

Regenerate ecosystem knowledge:

```bash
python3 scripts/gather_ecosystem_knowledge.py
```

## End of every turn (required)

Shadow worker **always** refreshes README live-status blocks:

```bash
python3 scripts/agent_shadow_worker.py run
```

Optional full refresh:

```bash
python3 scripts/agent_shadow_worker.py run --ecosystem --snapshot
python3 scripts/agent_shadow_worker.py install-cron   # every 5 min on your machine
```

README markers updated: root `README.md` + `docs/agent_audit_log/README.md`  
(script: `scripts/update_audit_readme.py`)

## Rules

1. Log before AND after every tool invocation when possible.
2. Always include `--omission` for what was not verified.
3. Never skip logging because an action seems small.
4. Do not log raw secrets — logger redacts common patterns.
5. **Always run shadow worker at end of turn** — keeps README + audit continuity current.
