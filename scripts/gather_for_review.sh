#!/usr/bin/env bash
# gather_for_review.sh — Comprehensive data collection for frontier-syntax review.
# Outputs to audit_reports/review_gather/
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

OUT="${ROOT}/audit_reports/review_gather"
mkdir -p "$OUT"

TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
GIT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')"
GIT_COMMIT="$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"

log() { echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$OUT/gather.log"; }

# Track pass/fail for summary
declare -A PHASE_STATUS
declare -A BUILD_STATUS
GATE_ISSUES=""
GATE_PHASES=""

log "=== gather_for_review started at $TIMESTAMP ==="
log "Branch: $GIT_BRANCH  Commit: $GIT_COMMIT"
log "Output: $OUT"

# ---------------------------------------------------------------------------
# PHASE 1: REPOSITORY STRUCTURE
# ---------------------------------------------------------------------------
phase1() {
  log "PHASE 1: Repository structure"
  local f="$OUT/phase1_structure.txt"
  {
    echo "# PHASE 1: REPOSITORY STRUCTURE"
    echo "# Generated: $TIMESTAMP"
    echo "# Branch: $GIT_BRANCH  Commit: $GIT_COMMIT"
    echo ""
    echo "## Full file list with sizes (excludes target, .git, node_modules)"
    echo ""
    find . \( -path './target' -o -path './.git' -o -path '*/node_modules' -o -path '*/node_modules/*' \) -prune -o \
      -type f -printf '%s\t%p\n' 2>/dev/null | sort -t$'\t' -k2 || \
      find . \( -path './target' -o -path './.git' -o -path '*/node_modules' \) -prune -o \
        -type f -exec stat -c '%s %n' {} \; 2>/dev/null | sort -k2
    echo ""
    echo "## Directory tree (depth 4)"
    echo ""
    if command -v tree >/dev/null 2>&1; then
      tree -L 4 -I 'target|.git|node_modules' --dirsfirst 2>/dev/null || true
    else
      find . \( -path './target' -o -path './.git' -o -path '*/node_modules' \) -prune -o \
        -print | sed 's|[^/]*/| |g' | head -5000
    fi
  } > "$f" 2>&1
  PHASE_STATUS[1]="ok"
  log "  -> $f"
}

# ---------------------------------------------------------------------------
# PHASE 2: SOURCE CODE
# ---------------------------------------------------------------------------
phase2() {
  log "PHASE 2: Source code"
  local inv="$OUT/phase2_rust_inventory.txt"
  local full="$OUT/phase2_key_modules_full.txt"
  local other="$OUT/phase2_other_src_preview.txt"
  local entry="$OUT/phase2_entry_points.txt"

  {
    echo "# PHASE 2: Rust source inventory (./src/**/*.rs)"
    echo "# Generated: $TIMESTAMP"
    echo ""
    while IFS= read -r f; do
      local lines
      lines=$(wc -l < "$f" | tr -d ' ')
      printf '%6s  %s\n' "$lines" "$f"
    done < <(find ./src -name '*.rs' -type f 2>/dev/null | sort)
    echo ""
    local total=0 count=0
    while IFS= read -r f; do
      local lines
      lines=$(wc -l < "$f" | tr -d ' ')
      total=$((total + lines))
      count=$((count + 1))
    done < <(find ./src -name '*.rs' -type f 2>/dev/null)
    echo "TOTAL: $count files, $total lines"
  } > "$inv" 2>&1

  {
    echo "# PHASE 2: Key module full content"
    echo "# Generated: $TIMESTAMP"
    echo ""
    local key_files=(
      "src/lib.rs"
      "src/main.rs"
      "src/ast.rs"
      "src/wasm_codegen.rs"
      "src/lexer/mod.rs"
      "src/parser/mod.rs"
    )
    for kf in "${key_files[@]}"; do
      if [[ -f "$kf" ]]; then
        echo "================================================================================"
        echo "FILE: $kf ($(wc -l < "$kf" | tr -d ' ') lines)"
        echo "================================================================================"
        cat "$kf"
        echo ""
      else
        echo "MISSING: $kf"
        echo ""
      fi
    done
  } > "$full" 2>&1

  {
    echo "# PHASE 2: Other src files (line count + first 30 lines)"
    echo "# Generated: $TIMESTAMP"
    echo ""
    local key_set=" src/lib.rs src/main.rs src/ast.rs src/wasm_codegen.rs src/lexer/mod.rs src/parser/mod.rs "
    while IFS= read -r f; do
      if [[ "$key_set" == *" $f "* ]]; then continue; fi
      local lines
      lines=$(wc -l < "$f" | tr -d ' ')
      echo "--------------------------------------------------------------------------------"
      echo "FILE: $f ($lines lines)"
      echo "--------------------------------------------------------------------------------"
      head -n 30 "$f"
      echo ""
    done < <(find ./src -name '*.rs' -type f 2>/dev/null | sort)
  } > "$other" 2>&1

  {
    echo "# PHASE 2: Entry points"
    echo "# Generated: $TIMESTAMP"
    echo ""
    echo "## src/lib.rs"
    if [[ -f src/lib.rs ]]; then
      echo "Lines: $(wc -l < src/lib.rs | tr -d ' ')"
      head -n 80 src/lib.rs
      echo "... (see phase2_key_modules_full.txt for full content)"
    fi
    echo ""
    echo "## src/main.rs"
    if [[ -f src/main.rs ]]; then
      echo "Lines: $(wc -l < src/main.rs | tr -d ' ')"
      head -n 80 src/main.rs
      echo "... (see phase2_key_modules_full.txt for full content)"
    fi
    echo ""
    echo "## Cargo.toml [[bin]] targets"
    grep -A3 '^\[\[bin\]\]' Cargo.toml 2>/dev/null || echo "(none found)"
    echo ""
    echo "## Cargo.toml [lib]"
    grep -A5 '^\[lib\]' Cargo.toml 2>/dev/null || echo "(none found)"
  } > "$entry" 2>&1

  PHASE_STATUS[2]="ok"
  log "  -> $inv, $full, $other, $entry"
}

# ---------------------------------------------------------------------------
# PHASE 3: WORKER DISCOVERY
# ---------------------------------------------------------------------------
phase3() {
  log "PHASE 3: Worker discovery"
  local f="$OUT/phase3_workers.txt"

  {
    echo "# PHASE 3: WORKER DISCOVERY"
    echo "# Generated: $TIMESTAMP"
    echo ""

    summarize_file() {
      local path="$1" type="$2"
      echo "================================================================================"
      echo "PATH: $path"
      echo "TYPE: $type"
      echo "LINES: $(wc -l < "$path" 2>/dev/null | tr -d ' ')"
      echo "--------------------------------------------------------------------------------"
      echo "## First 50 lines"
      head -n 50 "$path" 2>/dev/null || echo "(unreadable)"
      echo ""
      echo "## Imports / requires"
      if [[ "$path" == *.py ]]; then
        grep -E '^(import |from )' "$path" 2>/dev/null | head -n 30 || echo "(none)"
      elif [[ "$path" == *.sh ]]; then
        grep -E '^(source |\. )' "$path" 2>/dev/null | head -n 20 || echo "(none)"
        head -n 20 "$path" | grep -E '^#' || true
      elif [[ "$path" == *.yml ]] || [[ "$path" == *.yaml ]]; then
        head -n 20 "$path"
      else
        head -n 10 "$path" | grep -iE 'import|require' || echo "(none detected)"
      fi
      echo ""
    }

    echo "## *.worker.* files"
  } > "$f"

  local found=0
  while IFS= read -r p; do
    summarize_file "$p" "worker-pattern" >> "$f"
    found=$((found + 1))
  done < <(find . \( -path './target' -o -path './.git' -o -path '*/node_modules' \) -prune -o \
    -name '*.worker.*' -type f -print 2>/dev/null | sort)

  {
    echo "## worker_* files"
  } >> "$f"
  while IFS= read -r p; do
    summarize_file "$p" "worker-prefix" >> "$f"
    found=$((found + 1))
  done < <(find . \( -path './target' -o -path './.git' -o -path '*/node_modules' \) -prune -o \
    -name 'worker_*' -type f -print 2>/dev/null | sort)

  {
    echo "## scripts/*.py"
  } >> "$f"
  while IFS= read -r p; do
    summarize_file "$p" "python-script" >> "$f"
    found=$((found + 1))
  done < <(find ./scripts -maxdepth 1 -name '*.py' -type f 2>/dev/null | sort)

  {
    echo "## scripts/*.sh"
  } >> "$f"
  while IFS= read -r p; do
    summarize_file "$p" "shell-script" >> "$f"
    found=$((found + 1))
  done < <(find ./scripts -maxdepth 1 -name '*.sh' -type f 2>/dev/null | sort)

  {
    echo "## .github/workflows/*"
  } >> "$f"
  if [[ -d .github/workflows ]]; then
    while IFS= read -r p; do
      summarize_file "$p" "github-workflow" >> "$f"
      found=$((found + 1))
    done < <(find .github/workflows -type f 2>/dev/null | sort)
  else
    echo "(no .github/workflows directory)" >> "$f"
  fi

  {
    echo "## pie-extension"
  } >> "$f"
  if [[ -d pie-extension ]] || [[ -f pie-extension ]]; then
    find pie-extension -type f 2>/dev/null | while read -r p; do
      summarize_file "$p" "pie-extension" >> "$f"
      found=$((found + 1))
    done
  else
    echo "(pie-extension not found)" >> "$f"
  fi

  # Also capture root-level worker scripts
  {
    echo "## Root-level worker scripts"
  } >> "$f"
  for p in frontier_worker.py frontier_agent.py; do
    if [[ -f "$p" ]]; then
      summarize_file "$p" "root-worker" >> "$f"
      found=$((found + 1))
    fi
  done

  echo "" >> "$f"
  echo "TOTAL_WORKER_ARTIFACTS: $found" >> "$f"
  echo "$found" > "$OUT/.worker_count"

  PHASE_STATUS[3]="ok"
  log "  -> $f ($found artifacts)"
}

# ---------------------------------------------------------------------------
# PHASE 4: TESTING
# ---------------------------------------------------------------------------
phase4() {
  log "PHASE 4: Testing"
  local testlist="$OUT/phase4_test_files.txt"
  local integration="$OUT/phase4_integration_tests.txt"
  local examples="$OUT/phase4_examples.txt"

  {
    echo "# PHASE 4: Test files (*test* in name)"
    echo "# Generated: $TIMESTAMP"
    echo ""
    local count=0
    while IFS= read -r f; do
      local lines
      lines=$(wc -l < "$f" | tr -d ' ')
      printf '%6s  %s\n' "$lines" "$f"
      count=$((count + 1))
    done < <(find . \( -path './target' -o -path './.git' -o -path '*/node_modules' \) -prune -o \
      -iname '*test*' -name '*.rs' -type f -print 2>/dev/null | sort)
    if [[ $count -eq 0 ]]; then
      echo "(no *test*.rs files by filename; inline #[test] modules in src/)"
      echo ""
      echo "## Inline test modules (grep #[test] in src/)"
      grep -rl '#\[test\]' ./src --include='*.rs' 2>/dev/null | while read -r f; do
        local n
        n=$(grep -c '#\[test\]' "$f" 2>/dev/null || echo 0)
        echo "  $n tests in $f"
      done
    fi
    echo ""
    echo "## tests/ directory"
    find ./tests -type f 2>/dev/null | sort | while read -r f; do
      printf '%6s  %s\n' "$(wc -l < "$f" | tr -d ' ')" "$f"
    done
  } > "$testlist" 2>&1

  {
    echo "# PHASE 4: Integration tests"
    echo "# Generated: $TIMESTAMP"
    echo ""
    for f in tests/*.rs frontier-dex/tests/*.rs; do
      if [[ -f "$f" ]]; then
        echo "================================================================================"
        echo "FILE: $f ($(wc -l < "$f" | tr -d ' ') lines)"
        echo "================================================================================"
        cat "$f"
        echo ""
      fi
    done
    if ! ls tests/*.rs frontier-dex/tests/*.rs &>/dev/null; then
      echo "## tests/scrub_generated/ (Python scrub tests)"
      find ./tests -type f -name '*.py' 2>/dev/null | while read -r f; do
        echo "--- $f ($(wc -l < "$f" | tr -d ' ') lines) ---"
        head -n 40 "$f"
        echo ""
      done
    fi
  } > "$integration" 2>&1

  {
    echo "# PHASE 4: examples/*.fr"
    echo "# Generated: $TIMESTAMP"
    echo ""
    for f in examples/*.fr; do
      if [[ -f "$f" ]]; then
        echo "================================================================================"
        echo "FILE: $f ($(wc -l < "$f" | tr -d ' ') lines)"
        echo "================================================================================"
        cat "$f"
        echo ""
      fi
    done
  } > "$examples" 2>&1

  PHASE_STATUS[4]="ok"
  log "  -> $testlist, $integration, $examples"
}

# ---------------------------------------------------------------------------
# PHASE 5: BUILD
# ---------------------------------------------------------------------------
phase5() {
  log "PHASE 5: Build configuration"
  local cargo="$OUT/phase5_cargo_toml.txt"
  local config="$OUT/phase5_build_config.txt"
  local tree_native="$OUT/phase5_cargo_tree_native.txt"
  local tree_wasm="$OUT/phase5_cargo_tree_wasm.txt"

  {
    echo "# PHASE 5: All Cargo.toml files"
    echo "# Generated: $TIMESTAMP"
    echo ""
    find . \( -path './target' -o -path './.git' \) -prune -o -name 'Cargo.toml' -type f -print 2>/dev/null | sort | while read -r f; do
      echo "================================================================================"
      echo "FILE: $f"
      echo "================================================================================"
      cat "$f"
      echo ""
    done
  } > "$cargo" 2>&1

  {
    echo "# PHASE 5: Build configuration files"
    echo "# Generated: $TIMESTAMP"
    echo ""
    for f in .cargo/config.toml build.rs rust-toolchain.toml; do
      if [[ -f "$f" ]]; then
        echo "================================================================================"
        echo "FILE: $f"
        echo "================================================================================"
        cat "$f"
        echo ""
      else
        echo "MISSING: $f"
        echo ""
      fi
    done
  } > "$config" 2>&1

  log "  Running cargo tree (native)..."
  {
    echo "# cargo tree --depth 1 (native)"
    echo "# Generated: $TIMESTAMP"
    echo ""
    cargo tree --depth 1 2>&1
  } > "$tree_native" || true

  log "  Running cargo tree (wasm32)..."
  {
    echo "# cargo tree --target wasm32-unknown-unknown --depth 1"
    echo "# Generated: $TIMESTAMP"
    echo ""
    cargo tree --target wasm32-unknown-unknown --depth 1 2>&1
  } > "$tree_wasm" || true

  PHASE_STATUS[5]="ok"
  log "  -> $cargo, $config, $tree_native, $tree_wasm"
}

# ---------------------------------------------------------------------------
# PHASE 6: CURRENT STATE (run commands)
# ---------------------------------------------------------------------------
phase6() {
  log "PHASE 6: Current state (builds, tests, gates)"

  run_capture() {
    local name="$1"
    local outfile="$OUT/phase6_${name}.txt"
    shift
    log "  Running: $*"
    {
      echo "# Command: $*"
      echo "# Started: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
      echo ""
      "$@" 2>&1
      local ec=$?
      echo ""
      echo "# Exit code: $ec"
      echo "# Finished: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
      return $ec
    } | tee "$outfile"
    local ec=${PIPESTATUS[0]}
    if [[ $ec -eq 0 ]]; then
      BUILD_STATUS["$name"]="pass"
    else
      BUILD_STATUS["$name"]="fail"
    fi
    return 0
  }

  run_capture cargo_build cargo build || true
  run_capture cargo_build_wasm cargo build --target wasm32-unknown-unknown --no-default-features --features wasm-slim || true
  run_capture cargo_test_lib cargo test --lib || true
  run_capture cargo_clippy cargo clippy -- -D warnings || true
  run_capture tracking_gate python3 scripts/tracking.py gate || true
  run_capture verify_wasm_codegen python3 scripts/verify_wasm_codegen.py || true
  run_capture measure_wasm_size python3 scripts/measure_wasm_size.py || true

  # Extract gate info for summary
  if [[ -f "$OUT/phase6_tracking_gate.txt" ]]; then
    GATE_ISSUES=$(grep -E 'open|issue|FAIL|fail' "$OUT/phase6_tracking_gate.txt" 2>/dev/null | head -n 40 || true)
    GATE_PHASES=$(grep -E 'phase|Phase|PASS|FAIL|gate' "$OUT/phase6_tracking_gate.txt" 2>/dev/null | head -n 40 || true)
  fi

  PHASE_STATUS[6]="ok"
  log "  Phase 6 complete"
}

# ---------------------------------------------------------------------------
# PHASE 7: WORKER HEALTH
# ---------------------------------------------------------------------------
phase7() {
  log "PHASE 7: Worker health (--help checks)"
  local f="$OUT/phase7_worker_health.txt"

  {
    echo "# PHASE 7: Worker health checks"
    echo "# Generated: $TIMESTAMP"
    echo ""
    echo "Testing --help on python scripts in scripts/ matching worker/swarm/orchestrator patterns"
    echo ""
  } > "$f"

  local pass=0 fail=0 skip=0

  while IFS= read -r script; do
  {
    echo "--------------------------------------------------------------------------------"
    echo "SCRIPT: $script"
    echo "--------------------------------------------------------------------------------"
    if timeout 10 python3 "$script" --help >"$OUT/.tmp_help.txt" 2>&1; then
      echo "STATUS: PASS"
      head -n 30 "$OUT/.tmp_help.txt"
      pass=$((pass + 1))
    else
      local ec=$?
      if [[ $ec -eq 124 ]]; then
        echo "STATUS: TIMEOUT (10s — script may not support --help)"
      else
        echo "STATUS: FAIL (exit $ec)"
      fi
      head -n 30 "$OUT/.tmp_help.txt"
      fail=$((fail + 1))
    fi
    echo ""
  } >> "$f"
  done < <(find ./scripts -maxdepth 1 -name '*.py' -type f 2>/dev/null | \
    xargs -I{} basename {} | \
    grep -iE 'worker|swarm|orchestrator' | \
    while read -r b; do echo "./scripts/$b"; done | sort)

  # Also test root workers
  for script in frontier_worker.py frontier_agent.py; do
    if [[ -f "$script" ]]; then
      {
        echo "--------------------------------------------------------------------------------"
        echo "SCRIPT: $script"
        echo "--------------------------------------------------------------------------------"
        if timeout 10 python3 "$script" --help >"$OUT/.tmp_help.txt" 2>&1; then
          echo "STATUS: PASS"
          head -n 30 "$OUT/.tmp_help.txt"
          pass=$((pass + 1))
        else
          local ec=$?
          if [[ $ec -eq 124 ]]; then
            echo "STATUS: TIMEOUT (10s)"
          else
            echo "STATUS: FAIL (exit $ec)"
          fi
          head -n 30 "$OUT/.tmp_help.txt"
          fail=$((fail + 1))
        fi
        echo ""
      } >> "$f"
    fi
  done

  {
    echo ""
    echo "SUMMARY: pass=$pass fail=$fail"
  } >> "$f"

  rm -f "$OUT/.tmp_help.txt"
  echo "$pass" > "$OUT/.worker_health_pass"
  echo "$fail" > "$OUT/.worker_health_fail"

  PHASE_STATUS[7]="ok"
  log "  -> $f (pass=$pass fail=$fail)"
}

# ---------------------------------------------------------------------------
# PHASE 8: ERROR LOGS
# ---------------------------------------------------------------------------
phase8() {
  log "PHASE 8: Error logs"
  local f="$OUT/phase8_error_logs.txt"

  {
    echo "# PHASE 8: Error logs"
    echo "# Generated: $TIMESTAMP"
    echo ""
    echo "## Frontier/worker logs in /tmp"
    echo ""
    local tmpfound=0
    for pattern in '*frontier*' '*worker*' '*swarm*'; do
      for logf in /tmp/$pattern /tmp/$pattern.log; do
        if [[ -f "$logf" ]]; then
          echo "================================================================================"
          echo "FILE: $logf"
          echo "================================================================================"
          tail -n 200 "$logf" 2>/dev/null || cat "$logf"
          echo ""
          tmpfound=$((tmpfound + 1))
        fi
      done
    done
    find /tmp -maxdepth 2 \( -iname '*frontier*' -o -iname '*worker*' -o -iname '*swarm*' \) -type f 2>/dev/null | while read -r logf; do
      echo "================================================================================"
      echo "FILE: $logf"
      echo "================================================================================"
      tail -n 100 "$logf" 2>/dev/null
      echo ""
    done
    if [[ $tmpfound -eq 0 ]]; then
      echo "(no matching logs found in /tmp)"
    fi
    echo ""
    echo "## Root-level log files"
    for logf in *.log; do
      if [[ -f "$logf" ]]; then
        echo "================================================================================"
        echo "FILE: $logf"
        echo "================================================================================"
        tail -n 100 "$logf"
        echo ""
      fi
    done
    echo ""
    echo "## Recent build errors from Phase 6"
    echo ""
    for phase6f in "$OUT"/phase6_*.txt; do
      if [[ -f "$phase6f" ]]; then
        local errs
        errs=$(grep -iE 'error(\[|:|])|failed|panic' "$phase6f" 2>/dev/null | head -n 30 || true)
        if [[ -n "$errs" ]]; then
          echo "--- Errors in $(basename "$phase6f") ---"
          echo "$errs"
          echo ""
        fi
      fi
    done
  } > "$f" 2>&1

  PHASE_STATUS[8]="ok"
  log "  -> $f"
}

# ---------------------------------------------------------------------------
# PHASE 9: CONFIG FILES
# ---------------------------------------------------------------------------
phase9() {
  log "PHASE 9: Config files"
  local f="$OUT/phase9_config_files.txt"

  {
    echo "# PHASE 9: Configuration files"
    echo "# Generated: $TIMESTAMP"
    echo ""
  } > "$f"

  local configs=(
    .vscode/settings.json
    .vscode/tasks.json
    .vscode/launch.json
    .editorconfig
    .rustfmt.toml
    rustfmt.toml
    .cargo/config.toml
    rust-toolchain.toml
    .gitignore
    .cursor/environment.json
    .cursor/rules
    requirements-knowledge-engine.txt
    TRACKING.json
  )

  for cfg in "${configs[@]}"; do
    if [[ -f "$cfg" ]]; then
      {
        echo "================================================================================"
        echo "FILE: $cfg"
        echo "================================================================================"
        cat "$cfg"
        echo ""
      } >> "$f"
    elif [[ -d "$cfg" ]]; then
      {
        echo "================================================================================"
        echo "DIR: $cfg"
        echo "================================================================================"
        find "$cfg" -type f 2>/dev/null | while read -r sf; do
          echo "--- $sf ---"
          cat "$sf" 2>/dev/null
          echo ""
        done
      } >> "$f"
    else
      echo "MISSING: $cfg" >> "$f"
      echo "" >> "$f"
    fi
  done

  # .vscode directory listing
  if [[ -d .vscode ]]; then
    echo "## .vscode directory listing" >> "$f"
    find .vscode -type f >> "$f" 2>/dev/null
    echo "" >> "$f"
  fi

  PHASE_STATUS[9]="ok"
  log "  -> $f"
}

# ---------------------------------------------------------------------------
# PHASE 10: SUMMARY
# ---------------------------------------------------------------------------
phase10() {
  log "PHASE 10: Summary"
  local f="$OUT/summary.md"

  local rust_count=0 rust_loc=0
  while IFS= read -r rf; do
    rust_count=$((rust_count + 1))
    rust_loc=$((rust_loc + $(wc -l < "$rf" | tr -d ' ')))
  done < <(find ./src -name '*.rs' -type f 2>/dev/null)

  local worker_count
  worker_count=$(cat "$OUT/.worker_count" 2>/dev/null || echo "?")
  local wh_pass wh_fail
  wh_pass=$(cat "$OUT/.worker_health_pass" 2>/dev/null || echo "?")
  wh_fail=$(cat "$OUT/.worker_health_fail" 2>/dev/null || echo "?")

  {
    echo "# Review Gather Summary"
    echo ""
    echo "**Generated:** $TIMESTAMP"
    echo "**Git branch:** $GIT_BRANCH"
    echo "**Git commit:** $GIT_COMMIT"
    echo ""
    echo "## Codebase metrics"
    echo ""
    echo "| Metric | Value |"
    echo "|--------|-------|"
    echo "| Rust files (src/) | $rust_count |"
    echo "| Total LOC (src/) | $rust_loc |"
    echo "| Worker artifacts cataloged | $worker_count |"
    echo "| Worker --help pass/fail | $wh_pass / $wh_fail |"
    echo ""
    echo "## Build / test / gate status"
    echo ""
    echo "| Check | Status |"
    echo "|-------|--------|"
    for key in cargo_build cargo_build_wasm cargo_test_lib cargo_clippy tracking_gate verify_wasm_codegen measure_wasm_size; do
      local st="${BUILD_STATUS[$key]:-unknown}"
      echo "| $key | $st |"
    done
    echo ""
    echo "## Tracking gate excerpts"
    echo ""
    echo '```'
    if [[ -f "$OUT/phase6_tracking_gate.txt" ]]; then
      tail -n 60 "$OUT/phase6_tracking_gate.txt"
    else
      echo "(not captured)"
    fi
    echo '```'
    echo ""
    echo "## Open issues / phase status from gate"
    echo ""
    echo '```'
    echo "$GATE_ISSUES"
    echo "$GATE_PHASES"
    echo '```'
    echo ""
    echo "## Phase gather status"
    echo ""
    for i in 1 2 3 4 5 6 7 8 9 10; do
      echo "- Phase $i: ${PHASE_STATUS[$i]:-unknown}"
    done
    echo ""
    echo "## Package file index"
    echo ""
    find "$OUT" -maxdepth 1 -type f ! -name '.*' | sort | while read -r af; do
      local sz
      sz=$(wc -c < "$af" | tr -d ' ')
      echo "- [\`$(basename "$af")\`]($(basename "$af")) ($sz bytes)"
    done
  } > "$f"

  PHASE_STATUS[10]="ok"
  log "  -> $f"
}

# ---------------------------------------------------------------------------
# Consolidated package index
# ---------------------------------------------------------------------------
generate_full_package() {
  log "Generating full_review_package.md"
  local f="$OUT/full_review_package.md"

  local rust_count=0 rust_loc=0
  while IFS= read -r rf; do
    rust_count=$((rust_count + 1))
    rust_loc=$((rust_loc + $(wc -l < "$rf" | tr -d ' ')))
  done < <(find ./src -name '*.rs' -type f 2>/dev/null)

  local worker_count
  worker_count=$(cat "$OUT/.worker_count" 2>/dev/null || echo "?")

  {
    echo "# Frontier Syntax — Full Review Package"
    echo ""
    echo "**Generated:** $TIMESTAMP  "
    echo "**Branch:** \`$GIT_BRANCH\`  "
    echo "**Commit:** \`$GIT_COMMIT\`  "
    echo "**Output directory:** \`audit_reports/review_gather/\`"
    echo ""
    echo "---"
    echo ""
    echo "## Executive Summary"
    echo ""
    echo "This package consolidates a comprehensive gather-for-review snapshot of the"
    echo "frontier-syntax repository. It includes repository structure, source inventory,"
    echo "worker discovery, test artifacts, build configuration, live build/test/gate"
    echo "results, worker health checks, error logs, and configuration files."
    echo ""
    echo "| Metric | Value |"
    echo "|--------|-------|"
    echo "| Rust source files | $rust_count |"
    echo "| Total LOC (src/) | $rust_loc |"
    echo "| Worker artifacts | $worker_count |"
    echo ""
    echo "### Build / Gate Status"
    echo ""
    for key in cargo_build cargo_build_wasm cargo_test_lib cargo_clippy tracking_gate verify_wasm_codegen measure_wasm_size; do
      local st="${BUILD_STATUS[$key]:-unknown}"
      local icon="?"
      [[ "$st" == "pass" ]] && icon="✅"
      [[ "$st" == "fail" ]] && icon="❌"
      echo "- $icon **$key**: $st"
    done
    echo ""
    echo "---"
    echo ""
    echo "## Artifact Index"
    echo ""
    echo "| File | Description |"
    echo "|------|-------------|"
    echo "| [summary.md](summary.md) | Aggregated metrics and status |"
    echo "| [phase1_structure.txt](phase1_structure.txt) | File list + directory tree |"
    echo "| [phase2_rust_inventory.txt](phase2_rust_inventory.txt) | All src/*.rs line counts |"
    echo "| [phase2_key_modules_full.txt](phase2_key_modules_full.txt) | Full content: lib, main, ast, wasm_codegen, lexer, parser |"
    echo "| [phase2_other_src_preview.txt](phase2_other_src_preview.txt) | Other src files: 30-line previews |"
    echo "| [phase2_entry_points.txt](phase2_entry_points.txt) | Entry points and bin targets |"
    echo "| [phase3_workers.txt](phase3_workers.txt) | Worker/script/workflow discovery |"
    echo "| [phase4_test_files.txt](phase4_test_files.txt) | Test file inventory |"
    echo "| [phase4_integration_tests.txt](phase4_integration_tests.txt) | Integration tests |"
    echo "| [phase4_examples.txt](phase4_examples.txt) | examples/*.fr content |"
    echo "| [phase5_cargo_toml.txt](phase5_cargo_toml.txt) | All Cargo.toml files |"
    echo "| [phase5_build_config.txt](phase5_build_config.txt) | .cargo/config, build.rs, toolchain |"
    echo "| [phase5_cargo_tree_native.txt](phase5_cargo_tree_native.txt) | cargo tree --depth 1 |"
    echo "| [phase5_cargo_tree_wasm.txt](phase5_cargo_tree_wasm.txt) | cargo tree wasm32 --depth 1 |"
    echo "| [phase6_cargo_build.txt](phase6_cargo_build.txt) | cargo build output |"
    echo "| [phase6_cargo_build_wasm.txt](phase6_cargo_build_wasm.txt) | wasm build output |"
    echo "| [phase6_cargo_test_lib.txt](phase6_cargo_test_lib.txt) | cargo test --lib output |"
    echo "| [phase6_cargo_clippy.txt](phase6_cargo_clippy.txt) | clippy -D warnings |"
    echo "| [phase6_tracking_gate.txt](phase6_tracking_gate.txt) | tracking.py gate |"
    echo "| [phase6_verify_wasm_codegen.txt](phase6_verify_wasm_codegen.txt) | WASM codegen verify |"
    echo "| [phase6_measure_wasm_size.txt](phase6_measure_wasm_size.txt) | WASM size measurement |"
    echo "| [phase7_worker_health.txt](phase7_worker_health.txt) | Worker --help health |"
    echo "| [phase8_error_logs.txt](phase8_error_logs.txt) | Error logs |"
    echo "| [phase9_config_files.txt](phase9_config_files.txt) | Config files |"
    echo "| [gather.log](gather.log) | Script execution log |"
    echo ""
    echo "---"
    echo ""
    echo "## Key Excerpts"
    echo ""
    echo "### Tracking Gate (last 40 lines)"
    echo ""
    echo '```'
    if [[ -f "$OUT/phase6_tracking_gate.txt" ]]; then
      tail -n 40 "$OUT/phase6_tracking_gate.txt"
    fi
    echo '```'
    echo ""
    echo "### cargo build status"
    echo ""
    echo '```'
    if [[ -f "$OUT/phase6_cargo_build.txt" ]]; then
      tail -n 15 "$OUT/phase6_cargo_build.txt"
    fi
    echo '```'
    echo ""
    echo "### cargo build wasm status"
    echo ""
    echo '```'
    if [[ -f "$OUT/phase6_cargo_build_wasm.txt" ]]; then
      tail -n 15 "$OUT/phase6_cargo_build_wasm.txt"
    fi
    echo '```'
    echo ""
    echo "### Worker inventory (first 80 lines)"
    echo ""
    echo '```'
    if [[ -f "$OUT/phase3_workers.txt" ]]; then
      head -n 80 "$OUT/phase3_workers.txt"
    fi
    echo '```'
    echo ""
    echo "### Module inventory (src/*.rs)"
    echo ""
    echo '```'
    if [[ -f "$OUT/phase2_rust_inventory.txt" ]]; then
      cat "$OUT/phase2_rust_inventory.txt"
    fi
    echo '```'
    echo ""
    echo "---"
    echo ""
    echo "*End of full review package index.*"
  } > "$f"

  log "  -> $f"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
  phase1
  phase2
  phase3
  phase4
  phase5
  phase6
  phase7
  phase8
  phase9
  phase10
  generate_full_package

  # Cleanup temp markers
  rm -f "$OUT/.worker_count" "$OUT/.worker_health_pass" "$OUT/.worker_health_fail" "$OUT/.tmp_help.txt"

  log "=== gather_for_review complete ==="
  echo ""
  echo "REVIEW_PACKAGE_PATH=$OUT"
  echo "SUMMARY=$OUT/summary.md"
  echo "FULL_PACKAGE=$OUT/full_review_package.md"
}

main "$@"
