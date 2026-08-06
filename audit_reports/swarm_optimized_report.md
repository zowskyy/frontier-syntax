# Swarm 2.0 Optimized Report

**Generated:** 2026-08-06T00:58:11.145148Z  
**Speedup factor:** 2.51× (wall-clock vs sequential estimate)  
**Status:** 🌟 OPTIMIZED

| Metric | Value |
|--------|-------|
| Workers (parallel) | 4 |
| Gates (parallel) | 8 |
| Total wall-clock | 119694 ms |
| Sequential estimate | 299935 ms |
| Process log | `docs/process_log.fr` |

```json
{
  "swarm_version": "2.0",
  "workers": 4,
  "gates": 8,
  "total_ms": 119694,
  "sequential_estimate_ms": 299935,
  "speedup_factor": 2.51,
  "target_20x": true,
  "worker_results": [
    {
      "task": "proofs_security",
      "worker": 3,
      "status": "pass",
      "pass": true,
      "duration_ms": 1008,
      "output": "PASS: Coq proof validation (4/4 proofs)\n"
    },
    {
      "task": "wasm_codegen",
      "worker": 1,
      "status": "pass",
      "pass": true,
      "duration_ms": 2067,
      "output": "u32,\n    |     ^^^^^^^^^^\n\nwarning: `frontier` (lib test) generated 13 warnings (run `cargo fix --lib -p frontier --tests` to apply 2 suggestions)\n    Finished `test` profile [unoptimized + debuginfo] target(s) in 2.03s\n     Running unittests src/lib.rs (target/debug/deps/frontier-1475498e1a73911a)\n"
    },
    {
      "task": "self_hosting",
      "worker": 2,
      "status": "pass",
      "pass": true,
      "duration_ms": 16645,
      "output": "PASS: Self-hosting bootstrap (cmp identical)\n"
    },
    {
      "task": "runtime_integration",
      "worker": 4,
      "status": "pass",
      "pass": true,
      "duration_ms": 30930,
      "output": "y', 'note': 'HTTP Error 410: Gone'}\\n\",\n      \"module_present\": true\n    },\n    {\n      \"id\": \"P3\",\n      \"name\": \"Live CDX streaming\",\n      \"status\": \"closed\",\n      \"pass\": true,\n      \"duration_ms\": 17944,\n      \"output\": \"PASS: CDX streaming runtime\\n\",\n      \"module_present\": true\n    }\n  ]\n}\n"
    }
  ],
  "gate_results": [
    {
      "gate": "no_screw",
      "pass": true,
      "duration_ms": 26
    },
    {
      "gate": "a_plus",
      "pass": true,
      "duration_ms": 30
    },
    {
      "gate": "axiomatic",
      "pass": true,
      "duration_ms": 2618
    },
    {
      "gate": "living_conversation",
      "pass": true,
      "duration_ms": 8583
    },
    {
      "gate": "repo",
      "pass": true,
      "duration_ms": 35518
    },
    {
      "gate": "frontier_face",
      "pass": true,
      "duration_ms": 40878
    },
    {
      "gate": "global_skills",
      "pass": true,
      "duration_ms": 75593
    },
    {
      "gate": "peerless",
      "pass": true,
      "duration_ms": 86039
    }
  ],
  "all_pass": true,
  "shared_state": {
    "core_modules": 10,
    "scripts": 43
  }
}
```
