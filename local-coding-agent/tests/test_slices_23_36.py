# SPDX-License-Identifier: Apache-2.0
"""Tests for SLICE 23-36."""

from __future__ import annotations

from pathlib import Path

import pytest

from local_agent.benchmark.augmentation import AugmentationBenchmark
from local_agent.benchmark.e2e_tasks import E2ETaskRunner
from local_agent.benchmark.harness import BenchmarkHarness
from local_agent.benchmark.model import ModelBenchmark
from local_agent.config import AgentConfig
from local_agent.mobile import MobileCore, MobileResourceManager, MobileSecurity
from local_agent.model.mock import MockProvider
from local_agent.reliability.harness import ReliabilityHarness
from local_agent.release import ReleaseEngineering
from local_agent.types import AgentState


def test_reliability_harness(tmp_path: Path) -> None:
    harness = ReliabilityHarness(tmp_path)
    results = harness.run_suite()
    assert len(results) >= 2
    assert all(r.result == "PASS" for r in results)


def test_augmentation_benchmark(tmp_path: Path) -> None:
    bench = AugmentationBenchmark(tmp_path)
    result = bench.run_fixture("t1", "wrong", "per docs: validate_input()", "validate_input", ["validate_input()"])
    assert result.augmented_correct
    assert not result.baseline_correct


def test_model_benchmark(tmp_path: Path) -> None:
    provider = MockProvider()
    prompt = '{"type":"TOOL_CALL","tool":"list_files","arguments":{}}'
    provider.set_response(prompt, prompt)
    record = ModelBenchmark(tmp_path).run(provider, prompt)
    assert record.provider == "MockProvider"


def test_e2e_runner(package_root: Path, workspace_tmp: Path, tmp_path: Path) -> None:
    config = AgentConfig(workspace_root=workspace_tmp)
    runner = E2ETaskRunner(config, package_root / "fixtures", tmp_path)
    results = runner.run_all()
    assert len(results) == 10
    assert all(r.passed for r in results)


def test_benchmark_harness_desktop(package_root: Path) -> None:
    report = BenchmarkHarness(package_root, profile="desktop").run()
    assert report.summary["e2e_total"] == 10
    assert report.summary["reliability_total"] >= 2


def test_mobile_profiles() -> None:
    core = MobileCore()
    android = core.profile("android")
    ios = core.profile("ios")
    assert android.python_runtime
    assert not ios.python_runtime


def test_mobile_resource_manager() -> None:
    state = MobileResourceManager().assess(ram_mb=3072, storage_mb=1024)
    assert state.recommended_quant == "Q4_K_M"


def test_mobile_security_evidence(tmp_path: Path) -> None:
    path = MobileSecurity().write_evidence(tmp_path, "android")
    assert path.exists()


def test_release_engineering(package_root: Path) -> None:
    rel = ReleaseEngineering(package_root)
    gate = rel.security_gate()
    assert gate.unsafe_deserialization == 0
    rc = rel.validate_rc()
    assert rc["tests_passed"] is True


@pytest.fixture
def package_root() -> Path:
    return Path(__file__).resolve().parent.parent
