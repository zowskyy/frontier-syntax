# Getting Started with Frontier

## Prerequisites

```bash
rustc --version   # 1.75+
python3 --version
```

## Build

```bash
cargo build --bin frontier
```

## Verify

```bash
python3 build/arc_orchestrator.py --verify
cargo test --lib
```

## Interpret a program

```bash
python3 scripts/frontier_interpret.py test_program.frontier
```

## Query knowledge

```bash
python3 scripts/frontier_know.py "sort algorithm"
cargo run --bin frontier -- knowledge query "ReDoS"
```

## Deploy knowledge engine

```bash
bash scripts/deploy_knowledge_engine.sh
```
