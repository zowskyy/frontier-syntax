# /truth-verify

Run the Frontier verification pipeline (engine v3.0).

## Usage

```
/truth-verify [--quick] [--ci] [--full] [--phases=phase1,phase2]
```

## What it does

1. **Python engine** — unified orchestration instead of shell phases
2. **Property-based tests** — parser never panics, deterministic parse/hash
3. **Incremental cache** — `.verification_cache/` skips unchanged phases
4. **Parallel execution** — independent phases run concurrently
5. **Optional Docker sandbox** — host vs container hash comparison when Docker is available
6. **Mandatory Coq in CI** — `--ci` fails if `coqc` or proofs are missing
7. **Differential checks** — fuzzing, sample hash parity, WASM artifact presence

## Examples

```
/truth-verify --quick
/truth-verify --ci
/truth-verify --phases=fuzz,compare
```

## Equivalent command

```bash
./build_truth.sh --quick
python3 -m verification.engine --quick
```

## Outputs

- `verification/reports/` — environment, emulation, comparison, final report
- `proof/certificates/` — signed JSON certificate + SHA-256 sidecar
- `truth_certificate_*.txt` — human-readable certificate
- `.verification_cache/` — incremental phase cache

## Troubleshooting

Re-run a single phase:

```bash
python3 -m verification.engine --phases=fuzz --no-cache
```
