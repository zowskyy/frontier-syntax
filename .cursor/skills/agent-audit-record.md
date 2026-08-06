# Agent Audit Record — mandatory for this repo

See `agent-legal-record/.cursor/skills/agent-audit-record.md` for full skill.

After significant actions:

```bash
python3 agent-legal-record/scripts/agent_audit_logger.py record \
  --category tool_call --action "..." --why "..." --command "..." --verified
```

End of turn (cloud agent):

```bash
python3 agent-legal-record/scripts/agent_shadow_worker.py run
```

Private record repo: https://github.com/zowskyy/frontier-agent-legal-record
