# Frontier Agent Legal Record

**Owner:** zowskyy  
**Purpose:** Append-only audit trail of Cursor agent actions, decisions, and reproducibility instructions.  
**Status:** Private record repository — separate from `frontier-syntax` application code.

---

## Honest limitations (read first)

This system **does not** magically record everything Cursor does inside the IDE on your machine unless you run the hooks/daemons described below.

| Claim | True? |
|-------|-------|
| Every action **this cloud agent** takes via scripts in this repo can be logged with rationale | **Yes**, when agents call `agent_audit_logger.py` |
| Every keystroke in every Cursor chat on every device is auto-captured | **No** — requires Cursor product integration we do not control |
| The agent runs during **>5 min idle** without your prompt | **No** — agents are not persistent daemons between turns |
| A background worker **can** flush/sync logs on a schedule **you** enable | **Yes** — `agent_shadow_worker.py` + cron/systemd |
| Logs are legally admissible | **Not guaranteed** — consult counsel; we optimize for completeness and integrity |

**Integrity model:** JSONL append-only + git commits + optional push to this private repo. Tamper-evident via git history, not cryptographic notarization (unless you add that later).

---

## Layout

```
sessions/           # One JSONL per session + summary markdown
schema/             # JSON schema for entries
scripts/            # Logger, shadow worker, backfill, sync
.cursor/skills/     # Skill for future agents (copy to main repo)
```

---

## Quick start

```bash
# Log one action (from frontier-syntax or this repo)
python3 agent-legal-record/scripts/agent_audit_logger.py record \
  --category tool_call \
  --action "Ran tracking gate" \
  --why "User requested verification of phase status" \
  --command "python3 scripts/tracking.py gate"

# Shadow worker: idle flush + git commit + push (if REMOTE configured)
python3 agent-legal-record/scripts/agent_shadow_worker.py run

# Install idle checker (every 5 min) — YOU must enable on your host
# See scripts/install_audit_daemon.sh
```

---

## Entry requirements (every log line)

Each record **must** include:

1. **action** — what happened (imperative, specific)
2. **why** — decision rationale (no hand-waving)
3. **how_to_repeat** — command, script path, or skill reference
4. **honesty.verified_by_execution** — `true` only if command actually ran
5. **honesty.omissions** — what was *not* checked or could not be verified

---

## Sync to private GitHub

**Private repo created:** https://github.com/zowskyy/frontier-agent-legal-record (private)

The cloud agent token **could not push** to this repo (permission scope). **You** must push from a machine with your credentials:

```bash
bash agent-legal-record/scripts/sync_to_private_repo.sh
```

Or clone the private repo and copy `sessions/` manually.

Set in `agent-legal-record/.env` (not committed):

```
AUDIT_REMOTE=https://github.com/zowskyy/frontier-agent-legal-record.git
```

---

## Relationship to `docs/process_log.fr`

| Log | Audience | Format |
|-----|----------|--------|
| `process_log.fr` | Frontier training / lexicon | `.fr` components |
| `agent-legal-record/` | Legal / personal audit | JSONL + markdown |

Dual-write supported via `--also-process-log` flag on logger.
