# Archive Collector

**Package:** `scripts/archive_collector/`  
**Orchestrator:** `scripts/archive_collector_team.py`  
**Manifest:** `manifest/archive_collector.json`  
**Dataset:** `manifest/archive_dataset/`

## Overview

Anonymous Internet Archive CDX dataset collector for Frontier Syntax. Polls the Wayback Machine CDX API, classifies captures by structural signals (TLD, hostname keywords, path segments), and stores anonymized metadata — no PII.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  archive_collector_team.py                  │
│                     (orchestrator CLI)                      │
└──────────────┬──────────────────┬───────────────────────────┘
               │                  │
    ┌──────────▼─────────┐ ┌──────▼──────┐ ┌─────────────────┐
    │  S1 Discovery (7)  │ │ S2 Collect  │ │ S3 Classify (7) │
    │  W01–W07           │ │ W08–W14     │ │ W15–W21         │
    └──────────┬─────────┘ └──────┬──────┘ └────────┬────────┘
               │                  │                  │
               └──────────────────┼──────────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │  manifest/archive_dataset │
                    │  records.jsonl + state.json│
                    └───────────────────────────┘
```

## Supervisors

| Supervisor | Name | Workers |
|------------|------|---------|
| S1 | Discovery | W01_CDXScanner, W02_DomainShard, W03_ResumptionWalker, W04_PolitenessGate, W05_PrefixEnumerator, W06_NewCaptureWatcher, W07_ShadowMirror |
| S2 | Collection | W08_SnapshotMeta, W09_StoreWriter, W10_VersionChain, W11_DedupHash, W12_MimeFilter, W13_Checkpoint, W14_RateLimiter |
| S3 | Classification | W15_IndustryClassifier, W16_TopicTagger, W17_SemanticIndex, W18_TLDAnalyzer, W19_ContentMeta, W20_CrossDomainGraph, W21_DatasetExporter |

## Modes

| Mode | Description |
|------|-------------|
| `demo` | 5 seed hosts, limited CDX queries |
| `backfill` | Batch collection from seed list |
| `live` | Shadow mirror + incremental watchers |
| `full` | Backfill then live |

## Usage

```bash
# Demo run (5 hosts)
python3 scripts/archive_collector_team.py run --mode demo

# Full pipeline
python3 scripts/archive_collector_team.py run --mode full

# Verify installation
python3 scripts/verify_archive_collector.py
```

## Record Schema

Each line in `manifest/archive_dataset/records.jsonl`:

| Field | Description |
|-------|-------------|
| `id` | SHA-256 of host + path_hash + timestamp |
| `host` | Hostname only |
| `path_hash` | SHA-256 of URL path (no raw path stored) |
| `timestamp` | CDX capture timestamp |
| `industry` | Anonymous industry classification |
| `topics` | Topic tags from structural signals |
| `mime` | MIME type from CDX |
| `status` | HTTP status code |
| `collected_at` | ISO-8601 collection time |
| `supervisor` | Supervisor ID (S1–S3) |
| `worker` | Worker ID (W01–W21) |

## CDX Client

- Endpoint: `https://web.archive.org/cdx/search/cdx`
- Rate limit: 1 request/second (default)
- Pagination: `resumptionKey` support
- User-Agent: `FrontierSyntax-ArchiveCollector/1.0`

## Privacy

- No raw URL paths stored — only `path_hash`
- Classification uses TLD, hostname keywords, and path segment patterns only
- No cookies, credentials, or user-identifying data

## Outputs

- `manifest/archive_collector_run.json` — last run manifest
- `audit_reports/archive_collector_report.md` — human-readable report
- `manifest/archive_dataset/records.jsonl` — anonymous dataset
- `manifest/archive_dataset/state.json` — progress state
