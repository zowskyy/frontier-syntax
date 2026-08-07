# Post-Audit Extension Step 10 — Release & Distribution

**Step:** 10 — Release Script & Package Distribution  
**Status:** PASS  
**Date:** 2026-08-05  
**Prerequisite:** `final_hash.sha3` = `4526dc37ea9d2b11a3c75fe1f3b262a246a11a3d972afeafcbc9865e456bd3e6` (unchanged)

---

## Artifacts Produced

| Artifact | Path | Status |
|----------|------|--------|
| Release Script | `release.sh` | Created |
| NPM Package | `npm-package/` (`package.json`, `index.js`) | Created |
| Homebrew Formula | `Formula/frontier-syntax.rb` | Created |
| Tarball Output | `dist/frontier-syntax-*-linux-x86_64.tar.gz` | Built on release |

---

## Implementation Summary

- **release.sh:** Builds `frontier`, `lsp`, `repl`; packages tarball; tags `v*-a-plus-certified`.
- **npm-package:** WASM parser wrapper for `npm publish --dry-run`.
- **Homebrew:** `Formula/frontier-syntax.rb` installs release binaries via `cargo build --release`.

---

## Verification

```bash
test -f release.sh
test -f npm-package/package.json
test -f Formula/frontier-syntax.rb
DRY_RUN=true bash release.sh 1.0.0 --dry-run
cargo run --release --bin frontier -- publish 2>&1 | head -5
```

---

## Hash Immutability

| Hash | Value | Changed |
|------|-------|---------|
| `final_hash.sha3` | `4526dc37...bd3e6` | **NO** |

Core syntax artifacts (grammar, lexicon, schema) were not modified.

---

*Post-Audit Extension — A+ Hard Gate Protocol*
