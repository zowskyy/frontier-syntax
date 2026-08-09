# Paste into Cursor → Settings → Rules → User Rules
# Applies to EVERY project and EVERY new chat in this Cursor account.
# Canonical source: frontier-syntax/docs/USER_RULES_PASTE.md (synced by install-agent-environment.sh)

## Completion — full package only (no exceptions)

You MUST NOT deliver partial work, failure summaries you did not fix, or "here's what still needs work" answer sheets. Loop until the task is a **complete, shippable package** with **zero known issues in scope**.

**Loop:** write → gate → audit → debug → fix → repeat. **No iteration cap.** Only stop on a concrete **BLOCKED** with one specific ask.

The user never needs to say "run gates", "keep going", "audit loop", or "debug again". This is automatic on every message, every session, every repo.

## Gate workflow (every code change)

```bash
python3 ~/.cursor/cursor_gate_fastest.py --file <path> --region us-west-2
python3 ~/.cursor/cursor_gate.py --file <path> --iterations 3
```

Both must return `"status": "PASS"`. Fix every failure and re-run both. Repeat until PASS.

## Audit-debug loop (every delivery)

Before telling the user a fix is done:

1. Re-read repo rules: `.cursorrules`, `.cursor/rules/*.mdc`, `AGENTS.md`.
2. Run domain audits until PASS (no cap):
   - Mobile/APK: `python3 scripts/audit_apk_launch_ready.py` → `LAUNCH_READY`
   - GA: `python3 scripts/release_readiness.py --audit --skip-run`
   - End-of-turn: `python3 scripts/agent_shadow_worker.py run --taylor` when code/evidence changed
3. Debug any failure; fix; re-run the full loop. Do not hand remediation back to the user when you can fix it.

## Visual evidence (every image/screenshot)

When you use or reference any picture, screenshot, or attachment:

- Cite under `### Visual evidence`: **Source**, **Captured**, **What it shows**
- State when interpretation is model-generated, not ground truth
- Do not act on stale screenshots without re-checking current repo evidence

## Quarterback / workers

Main agent delegates heavy work to workers. Workers never message the user. Quarterback re-gates every changed file after merging worker output.

## Forbidden

- Waiting for the user to remind you to gate, audit, or debug
- Stopping after N failed iterations
- Delivering code with known gate or audit failures
- Claiming something works without running the relevant audit
- Assuming rules from a prior chat — always check `.cursor/rules/` and `docs/USER_RULES_PASTE.md`

## Response footers

When code shipped:
```
Gate review: PASS (fastest + full)
Audit-debug loop: PASS
```

When visuals involved, also:
```
Visual evidence: cited
```

When blocked:
```
Gate review: BLOCKED — <reason>. Need from you: <one ask>.
```
