# Security Policy

<!--
Licensed under SPDX-License-Identifier: Apache-2.0
-->

## Reporting a Vulnerability

Please report security vulnerabilities privately via your organization's standard security channel.
Do **not** open public issues for undisclosed vulnerabilities.

Include:

- Description of the issue and potential impact
- Steps to reproduce
- Affected versions / slices

## Threat model summary

| Trust level | Source | Policy |
|-------------|--------|--------|
| T0 | System (policy engine, workspace guard) | Trusted |
| T1 | User project files | Scoped to workspace |
| T2 | Retrieved knowledge | Untrusted wrapper; no authority |
| T3 | Model output | Untrusted; policy gate on every action |
| T4 | Plugin code | Subprocess + capability token (SLICE 18+) |
| T5 | External network | Disabled by default |

## Default security policy

```
READ=workspace; WRITE=transactional; DELETE=approval; SHELL=sandbox+capability;
NETWORK=disabled; PLUGIN=subprocess+token; SECRETS=deny
```

## Protected paths

The workspace guard denies read/write on:

- `.env`, `.env.*`
- `credentials*`, `*.pem`, `*.key`
- `.git/config`, `.git/hooks/*`

## Test runner sandboxing (SLICE 6)

`run_tests` executes only allowlisted commands (`pytest`, `python -m pytest`) with timeout and output size limits. No arbitrary shell.
