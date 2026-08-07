# Frontier Syntax — Release Checklist

**Normative gate:** No artifact ships until every pre-publish box is checked.  
**Orchestrator:** `python3 scripts/release_readiness.py --audit`

---

## Pre-publish gates (engineering)

### Wave 0 — Tier A evidence

- [ ] `python3 scripts/tracking.py gate` exits 0 (phases 0–3 validated)
- [ ] `cargo test --lib` — 40+ tests pass
- [ ] `python3 scripts/verify_wasm_codegen.py` — wasmtime 4/4 (`manifest/wasm_codegen_verify.json`)
- [ ] `python3 scripts/measure_wasm_size.py` — `met: true`, &lt;100 KB wasm-slim
- [ ] `python3 scripts/run_native_self_host.py` — native probe pass
- [ ] `python3 build/arc_orchestrator.py --verify` — ARC gates pass

### Wave 1 — Compiler hardening

- [ ] B1 — string/float literals return `Err` (not silent zero)
- [ ] B2 — browser export indices correct for `--browser`
- [ ] B3 — missing `main` returns error
- [ ] B4 — import declarations return error
- [ ] B5 — `@requires` error message accurate
- [ ] Negative unit tests in `wasm_codegen::`
- [ ] `docs/ARC_SYSTEM_STATUS.md` regenerated (`generate_arc_status.py`)
- [ ] `SECURITY.md` present

### Wave 2 — CI

- [ ] `.github/workflows/compiler-gate.yml` exists and blocks on failure
- [ ] wasmtime installed in CI (same as `.cursor/install.sh`)
- [ ] `tracking.py gate` blocking (no `|| true`)

### Wave 3 — Blueprint phases (GA only)

- [ ] Phase 4 — all 7 innovations have empirical acceptance tests
- [ ] Phase 5 — M5 full compiler (`manifest/compiler_self_host_mission.json`)
- [ ] Phase 7 — `cargo clippy -D warnings` clean, agent security re-scan

### Wave 4 — Release infrastructure

- [ ] `scripts/release_readiness.py --audit` implemented
- [ ] `manifest/production_readiness.json` current
- [ ] `CHANGELOG.md` updated for release

---

## RC phase

- [ ] Tag `v1.0.0-rc.1` after Wave 0–2 green
- [ ] `DRY_RUN=true bash release.sh 1.0.0-rc.1 --dry-run`
- [ ] `bash scripts/verify_cli.sh`
- [ ] `bash scripts/package-demo.sh`
- [ ] Install smoke from clean env (`frontier --help`, compile sample)
- [ ] Re-run `release_readiness.py --audit` ≥7 days apart with identical RC verdict

---

## Publish phase (only after `RC_READY` or `RELEASE_READY`)

- [ ] `bash release.sh 1.0.0` — native tarball in `dist/`
- [ ] `cargo publish --dry-run` then publish (if crates.io configured)
- [ ] `cd npm-package && npm publish --access public` (if npm configured)
- [ ] Git tag `v1.0.0-a-plus-certified`
- [ ] GitHub Release with `CHANGELOG.md` notes

---

## Post-publish

- [ ] Install smoke: npm install, tarball extract, `frontier compile examples/*.fr -t wasm`
- [ ] Announce per `docs/marketing/launch.md`
- [ ] Open next release tracking issue with this checklist pre-pasted

---

## External launch (GA — human gates)

- [ ] Discord server
- [ ] Website live (frontier.dev)
- [ ] Social media ready
- [ ] Waiting list active
- [ ] Launch date confirmed

---

## Pass criteria

| Target | Command | Exit |
|--------|---------|------|
| RC | `python3 scripts/release_readiness.py --audit` | `RC_READY` or `RELEASE_READY` |
| GA | same + Phase 4–7 + launch items | `RELEASE_READY` |
