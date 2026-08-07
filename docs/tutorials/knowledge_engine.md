# Knowledge Engine Tutorial

## 1. Run scrub pipeline

```bash
python3 frontier_agent.py "Run chat scrub pipeline"
```

## 2. Ingest into hypercube

```bash
cargo run --bin frontier -- knowledge ingest --file chat_scrub/WORKER_REPORT.json
```

## 3. Semantic query

```bash
cargo run --bin frontier -- knowledge query "WASM codegen gap"
python3 scripts/frontier_know.py "self-hosting"
```

## 4. MCP integration

```bash
cargo run --bin frontier -- mcp register --tool query_chat_knowledge
cargo run --bin frontier -- mcp list
```

## 5. Dashboard

Open `chat_scrub/dashboard.html` after running the scrub pipeline.
