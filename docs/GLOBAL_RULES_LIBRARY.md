# Global rules library

Rules apply in **three layers**. All three must stay in sync.

| Layer | Location | Scope |
|-------|----------|-------|
| **User Rules** | `docs/USER_RULES_PASTE.md` → Cursor Settings → Rules → User Rules | Every project, every chat (your Cursor account) |
| **Project rules** | `.cursor/rules/*.mdc` (`alwaysApply: true`) | This repo (and copies synced to cloud VMs) |
| **Root policy** | `.cursorrules` + `AGENTS.md` | This repo agents |

## Rule files (project layer)

| File | Purpose |
|------|---------|
| `ship-finished-work.mdc` | Gate until PASS; no partial deliveries |
| `visual-evidence-audit.mdc` | Cite images; audit-debug loop before delivery |
| `audit-debug-loop.mdc` | Multi-pass audit/debug until full package |
| `quarterback-worker.mdc` | Delegate to workers; re-gate merged changes |
| `ga-protocol.mdc` | Release readiness north star |

## Bootstrap (cloud agent / CI)

```bash
bash scripts/install-agent-environment.sh   # sync gates + rules to ~/.cursor/
python3 scripts/verify_global_rules.py      # must exit 0
```

`install-agent-environment.sh` copies:

- `cursor_gate*.py` → `~/.cursor/`
- `.cursor/rules/*.mdc` → `~/.cursor/rules/`
- `docs/USER_RULES_PASTE.md` → `~/.cursor/USER_RULES.md`
- Writes `manifest/global_rules.json`

## One-time setup (Cursor desktop — all repos)

1. Open **Cursor → Settings → Rules → User Rules**
2. Paste the full contents of `docs/USER_RULES_PASTE.md`
3. Save

Re-paste when `manifest/global_rules.json` `version` bumps.

## Verify

```bash
python3 scripts/verify_global_rules.py --json
```

CI runs this after `install-agent-environment.sh` in `gate-check.yml`.
