# Agent Audit Log + Taylor Ops Team — mandatory

Log **every** tool call. Then let the **Taylor Ops Team** handle the gambit.

## One command (preferred — end of every turn)

```bash
python3 scripts/agent_shadow_worker.py run --taylor
# or directly:
python3 scripts/taylor_ops_team.py run --mode end-of-turn
```

## Daily / full autonomous run

```bash
python3 scripts/taylor_ops_team.py run --mode daily
python3 scripts/taylor_ops_team.py run --mode full
python3 scripts/taylor_ops_team.py inventory
```

## Team of 7 → 3 groups

| Group | Name | Workers |
|-------|------|---------|
| 1 | TRUTH | GateKeeper, WasmVerifier, AuditGuardian |
| 2 | GITHUB | IssueMarshal, PrScout |
| 3 | CONTINUITY | KnowledgeScout, ContinuityShadow |

Inventory of all interaction scripts: `manifest/interaction_script_inventory.json`

## Log a single tool call

```bash
python3 scripts/agent_audit_hook.py \
  --tool <Shell|Read|Grep|Write|...> \
  --action "<what>" \
  --command "<exact command or path>" \
  --exit-code <code> \
  --verified
```

## Rules

1. Log before AND after every tool invocation when possible.
2. Always include `--omission` for what was not verified.
3. Never skip logging because an action seems small.
4. Do not log raw secrets — logger redacts common patterns.
5. **End of every turn:** `python3 scripts/agent_shadow_worker.py run --taylor`
6. Do **not** wait for the owner to re-prompt gates / issues / PRs / README — Taylor Ops Team covers it.
