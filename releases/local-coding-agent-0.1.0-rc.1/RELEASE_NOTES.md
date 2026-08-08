# local-coding-agent 0.1.0-rc.1

## Release type

Release candidate (RC). Suitable for integration testing. Public launch blocked until mobile device verification (blueprint check #6).

## Contents

- Python wheel and source distribution (`dist/`)
- SBOM and checksums
- Curated evidence package
- Audit manifest

## Install

```bash
pip install dist/local_coding_agent-0.1.0rc1-py3-none-any.whl
agent benchmark --profile desktop
```

## Blueprint status

All 37 implementation slices (0–36) verified with pytest. Taylor mission complete.

## Known limitations

- Mobile device runtime: `UNEXECUTED_REQUIRES_RUNTIME`
- Chroma optional dependency not included in base wheel
- Ollama/llama.cpp require separate local installation

## Verification

```bash
sha256sum -c SHA256SUMS
python3 -m pytest  # from extracted source
```
