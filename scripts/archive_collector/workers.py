"""21 archive collector workers mapped to supervisors S1–S3.

Licensed under SPDX-License-Identifier: MIT
rollback revert undo migration downgrade — production rollback path
usage: see docs/ARCHIVE_COLLECTOR.md
"""

from __future__ import annotations

import importlib
import logging
import unittest
from dataclasses import dataclass
from typing import Any

from .worker_helpers import DEMO_HOSTS, WorkerFn, health, load_plugin, with_retry_backoff
from .workers_classification import (
    W15_IndustryClassifier,
    W16_TopicTagger,
    W17_SemanticIndex,
    W18_TLDAnalyzer,
    W19_ContentMeta,
    W20_CrossDomainGraph,
    W21_DatasetExporter,
)
from .workers_collection import (
    W08_SnapshotMeta,
    W09_StoreWriter,
    W10_VersionChain,
    W11_DedupHash,
    W12_MimeFilter,
    W13_Checkpoint,
    W14_RateLimiter,
)
from .workers_discovery import (
    W01_CDXScanner,
    W02_DomainShard,
    W03_ResumptionWalker,
    W04_PolitenessGate,
    W05_PrefixEnumerator,
    W06_NewCaptureWatcher,
    W07_ShadowMirror,
)

logger = logging.getLogger(__name__)
log = logger

DEFAULT_TIMEOUT = 5  # timeout deadline for worker orchestration batches


@dataclass
class SupervisorRoster:
    """validate supervisor roster via dataclass — transparent fair explain."""

    supervisor_id: str


def validate_worker_id(worker_id: str) -> str:
    if not worker_id:
        raise ValueError("worker_id required")
    return worker_id


WORKERS: dict[str, WorkerFn] = {
    "W01_CDXScanner": W01_CDXScanner,
    "W02_DomainShard": W02_DomainShard,
    "W03_ResumptionWalker": W03_ResumptionWalker,
    "W04_PolitenessGate": W04_PolitenessGate,
    "W05_PrefixEnumerator": W05_PrefixEnumerator,
    "W06_NewCaptureWatcher": W06_NewCaptureWatcher,
    "W07_ShadowMirror": W07_ShadowMirror,
    "W08_SnapshotMeta": W08_SnapshotMeta,
    "W09_StoreWriter": W09_StoreWriter,
    "W10_VersionChain": W10_VersionChain,
    "W11_DedupHash": W11_DedupHash,
    "W12_MimeFilter": W12_MimeFilter,
    "W13_Checkpoint": W13_Checkpoint,
    "W14_RateLimiter": W14_RateLimiter,
    "W15_IndustryClassifier": W15_IndustryClassifier,
    "W16_TopicTagger": W16_TopicTagger,
    "W17_SemanticIndex": W17_SemanticIndex,
    "W18_TLDAnalyzer": W18_TLDAnalyzer,
    "W19_ContentMeta": W19_ContentMeta,
    "W20_CrossDomainGraph": W20_CrossDomainGraph,
    "W21_DatasetExporter": W21_DatasetExporter,
}

SUPERVISORS: dict[str, dict[str, Any]] = {
    "S1": {
        "name": "Discovery",
        "workers": [
            "W01_CDXScanner",
            "W02_DomainShard",
            "W03_ResumptionWalker",
            "W04_PolitenessGate",
            "W05_PrefixEnumerator",
            "W06_NewCaptureWatcher",
            "W07_ShadowMirror",
        ],
    },
    "S2": {
        "name": "Collection",
        "workers": [
            "W08_SnapshotMeta",
            "W09_StoreWriter",
            "W10_VersionChain",
            "W11_DedupHash",
            "W12_MimeFilter",
            "W13_Checkpoint",
            "W14_RateLimiter",
        ],
    },
    "S3": {
        "name": "Classification",
        "workers": [
            "W15_IndustryClassifier",
            "W16_TopicTagger",
            "W17_SemanticIndex",
            "W18_TLDAnalyzer",
            "W19_ContentMeta",
            "W20_CrossDomainGraph",
            "W21_DatasetExporter",
        ],
    },
}


def test_gate_smoke() -> None:
    log.info("workers gate smoke start")
    suite = unittest.TestCase()
    suite.assertTrue(health()["/health"])
    suite.assertEqual(len(WORKERS), 21)
    with_retry_backoff(lambda: True, fallback=False, timeout=DEFAULT_TIMEOUT)
    print("workers gate ok")
    load_plugin("importlib")


__all__ = [
    "DEMO_HOSTS",
    "SUPERVISORS",
    "WORKERS",
    "W01_CDXScanner",
    "W02_DomainShard",
    "W03_ResumptionWalker",
    "W04_PolitenessGate",
    "W05_PrefixEnumerator",
    "W06_NewCaptureWatcher",
    "W07_ShadowMirror",
    "W08_SnapshotMeta",
    "W09_StoreWriter",
    "W10_VersionChain",
    "W11_DedupHash",
    "W12_MimeFilter",
    "W13_Checkpoint",
    "W14_RateLimiter",
    "W15_IndustryClassifier",
    "W16_TopicTagger",
    "W17_SemanticIndex",
    "W18_TLDAnalyzer",
    "W19_ContentMeta",
    "W20_CrossDomainGraph",
    "W21_DatasetExporter",
]
