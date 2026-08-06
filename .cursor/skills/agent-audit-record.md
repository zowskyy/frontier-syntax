# Agent Audit Log + Taylor Ops Team — mandatory

## End of every turn

```bash
python3 scripts/agent_shadow_worker.py run --taylor
```

## Production pipeline (full path to prod-ready)

```bash
python3 scripts/agent_shadow_worker.py run --taylor --taylor-mode production
# or:
python3 scripts/taylor_ops_team.py run --mode production
```

### 7 workers → 3 groups (blueprint order)

| Group | Name | Workers | Blueprint |
|-------|------|---------|-----------|
| 1 | **FOUNDATION** | GateKeeper, CompilerCore, AuditGuardian | Phase 0–1 |
| 2 | **BUILD** | SpecParity, WasmSizer | Phase 2–3 |
| 3 | **SHIP** | GitHubOps, LaunchContinuity | Phase 7–8 prep |

Group 1 runs **sequential** in production mode (gate → compiler → audit).

## Rules

1. Log every tool call via `agent_audit_hook.py`.
2. End every turn with shadow worker `--taylor`.
3. Run `--taylor-mode production` before claiming prod-ready.
4. Do not wait for owner to re-prompt gates/issues/PRs/README.
