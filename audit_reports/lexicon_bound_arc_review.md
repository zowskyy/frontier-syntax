# Lexicon-Bound Worker — ARC Review

**Status:** LEXICON-BOUND — Every action documented, every user tagged

## Protocol

| Element | Implementation |
|---------|----------------|
| Lexicon Core | `frontier/lexicon/core.fr` |
| Lexicon Tag | `frontier/lexicon/tag.fr` |
| Bound Worker | `frontier/worker/lexicon_bound.fr` |
| User Tickets | `frontier/lexicon/user_ticket.fr` |
| Hard Gate | `frontier/lexicon/hard_gate.fr` |
| Python Wrapper | `scripts/lexicon_bound_worker.py` |
| Ingest | `scripts/lexicon_ingest.py` |
| Export (LLM training) | `scripts/lexicon_export.py` |
| Deploy Swarm | `scripts/deploy_lexicon_bound_swarm.py` (4×6 workers) |
| ARC Verify | `scripts/verify_lexicon_bound.py` |

## Lexicon Tag Structure

Every action carries: `action_id`, `user_id` (SHA3-256 hashed), `worker_id`,
`timestamp`, `action_type`, `input_hash`, `output_hash`, `lexicon_entry`,
`parent_action`, `documentation`, `knowledge_delta`.

## Commands

```bash
python3 scripts/deploy_lexicon_bound_swarm.py
python3 scripts/verify_lexicon_bound.py
python3 scripts/lexicon_ingest.py
python3 scripts/lexicon_export.py
python3 frontier_agent.py 'deploy lexicon bound worker'
```

## Logs

- `docs/lexicon_log.fr` — permanent Frontier-readable trace
- `manifest/lexicon_index.json` — queryable index
- `manifest/lexicon_export.jsonl` — LLM training export
