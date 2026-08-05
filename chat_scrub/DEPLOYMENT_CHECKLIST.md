# Frontier v2.0 — Deployment Checklist

**Source:** LAUNCH_CHECKLIST.md + deploy/ + scrub synthesis  
**Date:** 2026-08-05

---

## Pre-Deploy Verification

- [ ] `python3 build/arc_orchestrator.py --verify` — all ARC gates pass
- [ ] `cargo test --lib` — all unit tests pass
- [ ] `python3 scripts/verify_v2.py` — v2 hard gate pass
- [ ] `cargo build --release --target wasm32-unknown-unknown` — WASM builds
- [ ] `./deploy/health_check.sh` — health check passes

---

## Technical (Complete)

- [x] All 6 audit cycles complete
- [x] All 7 innovations implemented
- [x] All tests passing
- [x] All proofs validated
- [x] All hashes verified
- [x] Production binaries built
- [x] Deployment bundle created (`deploy/config.yaml`)
- [x] Monitoring configured (Prometheus, Grafana, Datadog)

---

## Services (deploy/config.yaml)

| Service | Port | Replicas |
|---------|------|----------|
| frontier-api | 8080 | 3 |
| frontier-migration | 8081 | 5 |
| frontier-lsp | 8082 | 2 |

---

## External Launch (Pending)

- [ ] Website live (frontier.dev)
- [ ] Discord server ready
- [ ] Social media ready
- [ ] Waiting list active
- [ ] Launch date confirmed

---

## Post-Deploy

- [ ] Submit WORKER_REPORT.json to Redis (`chat_scrub_report`, TTL 7 days)
- [ ] Trigger worker notify key (`chat_scrub_notify`) if immediate processing needed
- [ ] Monitor frontier-api / frontier-lsp health endpoints
- [ ] Backup verification (6-hour interval, 30-day retention)

---

## Rollback

```bash
git checkout cursor/frontier-syntax-cycle1-e39f
cargo build --release
./deploy/health_check.sh
```
