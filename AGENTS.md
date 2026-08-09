# Agent instructions — Schema / Cursor Gate

## AUTO-ENABLED — user never needs to remind you

This policy applies **automatically on every agent session** in this repo. The user does not need to say a command, keyword, or reminder. If they forget, you still follow this. No opt-in. No magic phrase.

## Completion policy

**Ship finished work only.** Do not stop at arbitrary iteration limits. Do not deliver half-filled answer sheets.

When you produce or modify code:

1. Run `python3 ~/.cursor/cursor_gate_fastest.py --file <path> --region us-west-2`
2. Run `python3 ~/.cursor/cursor_gate.py --file <path> --iterations 3`
3. Fix all failures and re-run until **both** return `"status": "PASS"`
4. Only then send the code to the user

If truly blocked, say **BLOCKED** with one specific ask — not a list of unfixed gate failures.

## Delegation (quarterback / workers)

The main agent is the **quarterback**; Task subagents are **workers**. Full policy: [`.cursor/rules/quarterback-worker.mdc`](.cursor/rules/quarterback-worker.mdc).

- **Quarterback** decomposes, delegates heavy work, merges results, **re-gates every changed file**, and delivers to the user.
- **Workers** implement only, gate their files, and return file list + gate status — they never message the user.
- **Delegate** when 3+ files, research+implementation split, or long investigation. **Inline** single small fixes.
- **Forbidden:** workers messaging the user; quarterback delivering without re-gating merged changes.

## Visual evidence + audit-debug loop

**Always on.** See [`.cursor/rules/visual-evidence-audit.mdc`](.cursor/rules/visual-evidence-audit.mdc) and [`.cursor/rules/audit-debug-loop.mdc`](.cursor/rules/audit-debug-loop.mdc).

- Cite every image/screenshot you reference (source, capture context, what it shows).
- Before delivery: re-read global rules, verify against cited evidence, run gates + domain audit loops until PASS (no iteration cap).

## Global rules library (all chats / all repos)

| Layer | File | Scope |
|-------|------|-------|
| User Rules | [`docs/USER_RULES_PASTE.md`](docs/USER_RULES_PASTE.md) | Paste into Cursor Settings → Rules → User Rules |
| Project rules | [`.cursor/rules/*.mdc`](.cursor/rules/) | Repo + synced to `~/.cursor/rules/` on VM boot |
| Verify | `python3 scripts/verify_global_rules.py` | CI + local check |

Full index: [`docs/GLOBAL_RULES_LIBRARY.md`](docs/GLOBAL_RULES_LIBRARY.md)

## Environment

Gate scripts are installed to `~/.cursor/` on every environment bootstrap via `scripts/install-agent-environment.sh`.
