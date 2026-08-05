# The Complete In-House Stack

**Everything is Frontier Syntax.** Zero external dependencies.

```
┌─────────────────────────────────────────────────────────────────┐
│                    EVERYTHING IS FRONTIER                         │
├─────────────────────────────────────────────────────────────────┤
│  LANGUAGE        → Frontier Syntax (grammar, design)              │
│  COMPILER        → frontier/bindings/compiler + browser_compiler │
│  RUNTIME         → frontier/bindings/ui + hardware               │
│  AI ENGINE       → frontier/bindings/ai → llama.cpp FFI          │
│  UI              → frontier/bindings/ui (native, not WebView)    │
│  STORAGE         → frontier/bindings/storage (SQLite)            │
│  NETWORK         → frontier/bindings/http                          │
│  AGENT SYSTEM    → frontier/lighthouse/agent_distiller           │
│  DISCOVERY       → frontier/lighthouse/discovery_engine          │
│  ARC             → frontier/lighthouse/arc_engine                │
│  DEPLOYMENT      → frontier/lighthouse/browser_compiler (11 targets) │
└─────────────────────────────────────────────────────────────────┘
```

## Module Map

| Component | Source | Compiles To |
|-----------|--------|-------------|
| ARC Engine | `frontier/lighthouse/arc_engine.frontier` | native binary |
| Discovery Engine | `frontier/lighthouse/discovery_engine.frontier` | native binary |
| Agent Distiller | `frontier/lighthouse/agent_distiller.frontier` | native binary |
| Browser Compiler | `frontier/lighthouse/browser_compiler.frontier` | `wasm_compiler.wasm` |
| Water Pump Tracker | `examples/lighthouse/water_pump_tracker.frontier` | ~3MB native |
| Mobile Runtime | `frontier/bindings/runtime.frontier` | `.so` / `.a` |
| Package Registry | `frontier/lighthouse/registry.frontier` | API server |

## Build

```bash
cargo build --release
./target/release/frontier validate frontier/lighthouse/arc_engine.frontier
./target/release/frontier validate examples/lighthouse/water_pump_tracker.frontier
```

## Principles

- No JavaScript frameworks, Python libraries, npm, pip, or third-party crates in application logic
- Every line compiles through **your** Frontier compiler
- Written once in Frontier → 11 platform targets

See [LIGHTHOUSE_INTEGRATION.md](LIGHTHOUSE_INTEGRATION.md) for sync with the Lighthouse agent UI.
