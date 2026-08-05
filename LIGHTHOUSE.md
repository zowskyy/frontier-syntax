# Lighthouse Integration

Frontier Syntax is the language layer; [Lighthouse (mia.loa)](https://github.com/zowskyy/mia.loa) is the agent that generates Frontier code and compiles it in the browser.

## Data Flow

```
User describes idea (Lighthouse)
    ↓
Discovery engine surfaces connections
    ↓
ARC generates .fr source (or uses examples/community templates)
    ↓
frontier-parser.js validates (Cycle 1 lexer + WASM when available)
    ↓
browser-compiler.js compiles via wasm_compiler.wasm
    ↓
Native binary download — zero npm, zero Node.js
```

## Asset Sync

### Frontier → Lighthouse

```bash
# In frontier-syntax repo:
./scripts/build-wasm.sh
LIGHTHOUSE_HOME=/path/to/mia.loa ./scripts/sync-to-lighthouse.sh

# In Lighthouse repo:
node assemble.js --item wasm-compiler
```

### Lighthouse → Frontier

```bash
# Community templates originate in Lighthouse assemble.js
# Canonical copies live in examples/community/
cp -r /path/to/mia.loa/frontier/templates/* examples/community/
```

## API Contract (browser-compiler.js)

The WASM module (`crates/frontier-wasm`) exports:

| Export | Purpose |
|--------|---------|
| `memory` | Linear memory for JSON I/O |
| `alloc` / `free` | Buffer management |
| `parse` | Validate source, return token count + errors |
| `compile` | Compile to LHN1 capsule (native codegen in progress) |
| `get_targets` | List 11 platform targets |
| `get_result_length` | Result buffer size |

Input format: `{"source": "...", "target": "linux-x64"}`

## Environment Variables

| Variable | Used by | Purpose |
|----------|---------|---------|
| `FRONTIER_HOME` | Lighthouse | Path to frontier-syntax checkout |
| `FRONTIER_COMPILER` | Lighthouse server | Path to `target/release/frontier` CLI |
| `LIGHTHOUSE_HOME` | frontier-syntax sync script | Path to mia.loa checkout |

## Shared Formats

### LHN1 Capsule (offline compile)

```
[u32 meta_len][meta JSON][u32 src_len][source UTF-8]
meta.magic = "LHN1"
```

Used by: `browser-compiler.js`, `frontier-wasm`, `frontier-cli compile`

## Version Alignment

| Lighthouse | Frontier Syntax | Notes |
|------------|-----------------|-------|
| v1.0.2 | v2.0.0 | Discovery engine + assemble.js |
| PR #5 | `cursor/lighthouse-integration-984d` | Browser compiler + templates |
