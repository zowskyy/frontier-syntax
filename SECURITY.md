# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | Yes       |
| &lt; 1.0  | No        |

## Reporting a Vulnerability

Email security reports to the repository owner via GitHub private vulnerability reporting, or open a **private** security advisory on [zowskyy/frontier-syntax](https://github.com/zowskyy/frontier-syntax/security/advisories).

Please include:

- Description and impact
- Steps to reproduce
- Affected version / commit SHA
- Suggested fix (optional)

We aim to acknowledge reports within 7 days. Critical issues affecting WASM sandbox escape or agent code execution will be prioritized.

## Scope

In scope:

- `src/wasm_codegen.rs` — incorrect codegen or silent wrong results
- `frontier_agent.py` / agent scripts — unsafe execution or injection
- `.cursor/install.sh` — supply-chain or arbitrary code execution

Out of scope:

- Third-party dependencies (report upstream)
- Stubs marked `NOT VERIFIED` in `PROJECT_BLUEPRINT.md` Phase 4

## Disclosure

Coordinated disclosure preferred. We will credit reporters in release notes unless anonymity is requested.
