# Architecture

<!--
Licensed under SPDX-License-Identifier: Apache-2.0
-->

## Overview

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Model        │────▶│ Output       │────▶│ Policy       │
│ Provider     │     │ Parser       │     │ Engine       │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
┌──────────────┐     ┌──────────────┐            ▼
│ Audit Log    │◀────│ Tool         │◀─── authorize()
│ (SQLite)     │     │ Registry     │
└──────────────┘     └──────┬───────┘
                            │
                     ┌──────▼───────┐
                     │ Edit Engine  │
                     │ (transaction)│
                     └──────┬───────┘
                            │
                     ┌──────▼───────┐
                     │ Workspace    │
                     │ Guard        │
                     └──────────────┘
```

## Module boundaries (SLICE 0–8)

| Module | Responsibility |
|--------|----------------|
| `config` | Validated settings; secrets from env only |
| `workspace` | Path resolution, traversal/symlink protection |
| `audit` | Append-only event store |
| `model/` | Provider abstraction (mock, ollama, llama_cpp) |
| `output` | Structured response parsing |
| `tools/` | Tool registry and handlers |
| `policy` | Deterministic authorization |
| `edit_engine` | Hash-checked transactional edits |

## Data flow

1. User task → audit `TASK_CREATED`
2. Model generates structured JSON → output parser validates
3. Tool request → policy engine authorizes → audit `TOOL_REQUEST` or `POLICY_DENIED`
4. Mutating tools → edit engine (hash check, temp copy, atomic commit) → audit `FILE_EDITED`

## Future slices

- SLICE 9+: Test runner hardening, knowledge store, agent loop, plugins
