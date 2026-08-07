# /archive-collector

Run the Frontier Syntax Archive Collector pipeline (21 workers / 3 supervisors).

## Usage

```
/archive-collector [--mode=demo|backfill|live|full] [--sequential]
```

## What it does

1. **S1 Discovery** — CDX scanning, domain sharding, resumption walking, politeness gate, shadow mirror
2. **S2 Collection** — snapshot metadata, storage, dedup, mime filter, checkpoints
3. **S3 Classification** — industry/topic tagging, semantic index, TLD analysis, dataset export

## Examples

```
/archive-collector --mode=demo
/archive-collector --mode=backfill
/archive-collector --mode=live
/archive-collector --mode=full
```

## Equivalent command

```bash
python3 scripts/archive_collector_team.py run --mode demo
python3 scripts/verify_archive_collector.py
```

## Outputs

- `manifest/archive_dataset/records.jsonl` — anonymous CDX dataset
- `manifest/archive_dataset/state.json` — collector progress state
- `manifest/archive_collector_run.json` — last run manifest
- `audit_reports/archive_collector_report.md` — human-readable report

## Seed hosts (demo)

- wikipedia.org
- archive.org
- github.com
- mozilla.org
- python.org
