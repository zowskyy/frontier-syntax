# Get Help — You Don't Need to Understand GitHub

If issues, pull requests, and the request system are confusing and slowing you down, **use this instead**.

## One command

```bash
python3 scripts/get_help.py "describe your problem in normal words"
```

Examples:

```bash
python3 scripts/get_help.py "my build fails"
python3 scripts/get_help.py "nothing is moving forward"
python3 scripts/get_help.py "I don't understand how to deploy this"
```

You get back a **request ID** (like `H-ABC123`). That's it. No GitHub required.

## Check what's blocking you

```bash
python3 scripts/get_help.py blocked
```

This scans open requests, waiting changes, and validation failures — then tells you in plain English what's slowing progress.

## Check your request status

```bash
python3 scripts/get_help.py status
python3 scripts/get_help.py status H-ABC123
```

## In Cursor

- Type `/get-help` or say **"get help with …"**
- The agent runs the system for you and explains in simple terms

## Install in your other repos

Copy the system to any git repo:

```bash
bash scripts/install_help_system.sh /path/to/your-other-repo
```

Then in that repo:

```bash
python3 scripts/get_help.py register
python3 scripts/get_help.py "your problem here"
```

All repos register in `~/.frontier/help/repos.json` for cross-repo status:

```bash
python3 scripts/get_help.py --all-repos blocked
```

## What happens behind the scenes (you can ignore this)

| You say | System does |
|---------|-------------|
| "my build fails" | Creates request `H-…`, searches for existing fixes, tracks work |
| "what's blocking me" | Scans issues, PRs, gates — reports in plain language |
| "status" | Shows your open requests |

You never need to:
- Open a GitHub issue manually
- Understand pull requests
- Figure out which issue blocks what

## Files

| File | Purpose |
|------|---------|
| `scripts/get_help.py` | Main entry point |
| `scripts/help_system/` | Core library (portable) |
| `scripts/install_help_system.sh` | Install into other repos |
| `manifest/help_config.json` | Per-repo settings |
| `manifest/help_requests.jsonl` | Your requests (local) |
| `~/.frontier/help/repos.json` | Cross-repo registry |

## For agents

See `.cursor/skills/help-triage.md` — agents must use plain language and never tell users to "open an issue."
