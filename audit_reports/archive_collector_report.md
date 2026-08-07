# Archive Collector Report

**Run ID:** `20260807T035948Z`  
**Mode:** `demo`  
**Started:** 2026-08-07T03:59:48.877859Z  
**Finished:** 2026-08-07T03:59:57.140144Z  
**Overall:** PASS  

## Supervisors (21 workers → 3 groups)

| Supervisor | Name | Workers |
|------------|------|---------|
| S1 | Discovery | W01–W07 |
| S2 | Collection | W08–W14 |
| S3 | Classification | W15–W21 |

## S1: Discovery — PASS

- **W01_CDXScanner** — PASS: 14 records — scanned 5 hosts
- **W04_PolitenessGate** — PASS: 0 records — rate limit 1.0s

## S2: Collection — PASS

- **W09_StoreWriter** — PASS: 126 records — dataset has 126 records
- **W13_Checkpoint** — PASS: 126 records — checkpoint saved

## S3: Classification — PASS

- **W15_IndustryClassifier** — PASS: 100 records — industry classify
- **W21_DatasetExporter** — PASS: 126 records — export meta

Dataset: `manifest/archive_dataset/`
Manifest: `manifest/archive_collector_run.json`
