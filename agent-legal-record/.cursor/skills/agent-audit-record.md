# Agent Audit Record — Cursor skill

When working on zowskyy/frontier-syntax (or any repo with `agent-legal-record/`):

## Mandatory behavior

1. **After every significant action** (tool call that changes code, runs verification, creates PR, makes a decision), append an audit entry:

```bash
python3 agent-legal-record/scripts/agent_audit_logger.py record \
  --category tool_call \
  --action "<what you did>" \
  --why "<why — tie to user goal or blueprint slice>" \
  --command "<exact command>" \
  --script "<script path if applicable>" \
  --skill "agent-audit-record" \
  --verified \
  --omission "<what you did NOT verify>"
```

2. **Honesty fields are required**
   - Use `--verified` ONLY if you ran the command and saw output
   - Use `--omission` for anything not checked
   - Use `--cannot-verify` for things impossible in this environment

3. **End of every user turn**: run shadow worker sync if on cloud agent:

```bash
python3 agent-legal-record/scripts/agent_shadow_worker.py run --sync
```

## What you cannot claim

- Do not claim idle logging happens automatically without cron/shadow worker
- Do not claim legal admissibility
- Do not omit failed commands — log them with `category=error`

## Categories

`user_prompt` | `tool_call` | `decision` | `git` | `pr` | `limitation` | `idle_flush` | `error` | `backfill`

## Private repo

Remote: `zowskyy/frontier-agent-legal-record` (private). Sync via shadow worker `--sync`.
