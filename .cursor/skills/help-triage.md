# Help Triage Skill

Use this skill whenever the user says "get help", "I'm stuck", "nothing is working", "what's blocking progress", or shows confusion about GitHub/issues/PRs.

## Core principle

**The user describes problems. The system handles GitHub.**

Never instruct the user to:
- Open a GitHub issue
- Create a pull request
- Understand issue numbers or PR mechanics
- Navigate the GitHub request/approval UI

## Commands

| User intent | Run |
|-------------|-----|
| Any problem / question | `python3 scripts/get_help.py "<their words>"` |
| What's blocking me? | `python3 scripts/get_help.py blocked` |
| Status of my requests | `python3 scripts/get_help.py status` |
| Specific request | `python3 scripts/get_help.py status H-XXXXXX` |
| All repos blocked | `python3 scripts/get_help.py --all-repos blocked` |
| Install in another repo | `bash scripts/install_help_system.sh /path/to/repo` |

## Response template

```
✅ Request received: H-XXXXXX

[One sentence summary of what we understood]

Status: [received / investigating / in progress]

No action needed from you. Check anytime with:
  python3 scripts/get_help.py status H-XXXXXX
```

## When GitHub work happens behind the scenes

- Similar open work → link instead of duplicate
- New bugs/features → auto-create tracked item with `get-help` label
- Stalled PRs → report as "change waiting to land"
- Gate failures → report as "validation hasn't passed yet"

## Cross-repo

Registry: `~/.frontier/help/repos.json`

Each repo has `manifest/help_config.json` and `manifest/help_requests.jsonl`.

Install into any repo:
```bash
bash scripts/install_help_system.sh /path/to/other-repo
```

## Integration with agents

- `frontier_agent.py` handles maintainer automation — do not route users there
- `get_help.py` is the **user-facing** entry point
- Tier A gates (`scripts/tracking.py gate`) determine when work is truly done
