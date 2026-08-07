# Get Help

You are helping a user who does **not** understand GitHub issues, pull requests, or the request system.

## What to do

1. Ask what they need in plain language — or use their message directly.
2. Run the Get Help system:

```bash
python3 scripts/get_help.py "<user's problem in their words>"
```

For status or blockers:

```bash
python3 scripts/get_help.py blocked
python3 scripts/get_help.py status
```

3. Report back using **plain language only**:
   - Give them a request ID like `H-ABC123`
   - Say "no action needed from you" when appropriate
   - **Never** tell them to "open an issue" or "create a PR"

## Rules

- Do NOT explain GitHub mechanics unless they explicitly ask
- Do NOT use words like "issue", "PR", "pull request" in user-facing replies — use "request", "tracked fix", "change waiting to land"
- If work is stalled, run `python3 scripts/get_help.py blocked` and summarize simply
- For cross-repo view: `python3 scripts/get_help.py --all-repos blocked`

## Examples

User: "nothing is moving forward"
→ Run `python3 scripts/get_help.py blocked` and explain what's stuck in simple terms

User: "my build fails"
→ Run `python3 scripts/get_help.py "my build fails"` and give them the request ID

User: "what happened to my last request"
→ Run `python3 scripts/get_help.py status`
