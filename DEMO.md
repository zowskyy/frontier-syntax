# Frontier CLI — Demo Guide

A 3-minute walkthrough you can run live or record.

## Before You Present

```bash
cargo build --release --bin frontier
```

## Run the Demo

| Mode | Command | Best for |
|------|---------|----------|
| Auto (recording) | `./scripts/demo.sh` | Screen capture, async sharing |
| Live (pauses) | `./scripts/demo.sh --present` | Conference talks, investor demos |

## Talking Points (60 seconds each)

### 1. The Language
> "Frontier is a formally verifiable language. Contracts like `@requires` and `@ensures` are first-class — not bolted on."

Show `examples/showcase.fr` — fibonacci with proof annotations.

### 2. The Toolchain
> "One binary handles parse, compile, hash, and knowledge-driven optimization."

Run `frontier --help` — point out `compile`, `knowledge`, `shell`, `watch`.

### 3. Knowledge Hypercube
> "70+ years of algorithm history, encoded in a dimensional solver. The compiler picks the optimal sort for your data shape."

```bash
frontier knowledge suggest sort list::i32
frontier knowledge ancestry sort
```

### 4. Compile + Profile
> "Full pipeline with real timings — lex, parse, type-check, knowledge lookup, codegen."

```bash
frontier compile examples/showcase.fr -t wasm -O -p
```

Highlight the profile table and the algorithm applied to codegen.

### 5. Interactive Mode (optional encore)
```bash
frontier shell
# then type: knowledge suggest hash list::i32
```

## One-Liner Proof

```bash
./scripts/verify_cli.sh && echo "✅ Verified"
```

## Files to Show

| File | Why |
|------|-----|
| `examples/showcase.fr` | Clean v2.0 demo program |
| `src/cli/` | Modular CLI architecture |
| `src/knowledge/` | Hypercube solver |
| `scripts/demo.sh` | Repeatable demo flow |
