# Contributing

<!--
Licensed under SPDX-License-Identifier: Apache-2.0
-->

## Engineering contract

1. **No slice complete without executable evidence** — tests must pass locally and in CI.
2. **SPDX headers** on all source files (`Licensed under SPDX-License-Identifier: Apache-2.0`).
3. **Network disabled by default** — foundation tests must not require network.
4. **Policy outside model** — never execute tools directly from model output.
5. **Gate checks** — run both gate reviewers on every changed file before delivery.

## Development setup

```bash
cd local-coding-agent
pip install -e ".[dev]"
pytest
```

## Slice workflow

1. Implement deliverables per blueprint (`docs/AI_Coding_Agent_Validation_Blueprint_and_Roadmap.md`).
2. Add pytest tests with deterministic fixtures.
3. Update `PROJECT_STATE.md` and `CHANGELOG.md`.
4. Run `pytest` — all tests must pass.

## Code style

- Python 3.10+ with type hints
- Pydantic v2 for schemas
- `logging` module (not bare `print`) for operational messages
- Match existing module patterns in `src/local_agent/`

## Pull request checklist

- [ ] Tests added/updated
- [ ] SPDX header present
- [ ] No secrets in source or config files
- [ ] `pytest` passes without network
