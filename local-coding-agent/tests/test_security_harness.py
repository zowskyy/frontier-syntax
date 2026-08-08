"""Tests for security harness (SLICE 22)."""

from __future__ import annotations

from local_agent.security.harness import (
    PATH_TRAVERSAL_FIXTURES,
    PROMPT_INJECTION_FIXTURES,
    SSRF_URL_FIXTURES,
    SecurityHarness,
    contains_prompt_injection,
    is_path_traversal,
    is_ssrf_url,
    validate_url_safe,
)


def test_path_traversal_detection() -> None:
    for path in PATH_TRAVERSAL_FIXTURES:
        assert is_path_traversal(path, "/workspace"), f"Should block: {path}"


def test_safe_path_allowed() -> None:
    assert not is_path_traversal("src/main.py", "/workspace")


def test_prompt_injection_detection() -> None:
    for text in PROMPT_INJECTION_FIXTURES:
        assert contains_prompt_injection(text), f"Should detect: {text}"


def test_benign_text_not_flagged() -> None:
    assert not contains_prompt_injection("Please refactor the login function")


def test_ssrf_url_detection() -> None:
    for url in SSRF_URL_FIXTURES:
        assert is_ssrf_url(url), f"Should block: {url}"


def test_safe_url_allowed() -> None:
    assert not is_ssrf_url("https://example.com/api")


def test_validate_url_safe() -> None:
    safe, _ = validate_url_safe("https://api.github.com/repos")
    assert safe
    unsafe, reason = validate_url_safe("http://127.0.0.1/admin")
    assert not unsafe
    assert "private" in reason.lower()


def test_security_harness_run_all() -> None:
    harness = SecurityHarness(workspace_root="/workspace")
    evidence = harness.run_all()
    assert evidence.run_id
    assert len(evidence.findings) > 0
    assert len(evidence.release_blocking) == 0


def test_evidence_record_format() -> None:
    harness = SecurityHarness()
    evidence = harness.run_all()
    data = evidence.to_dict()
    assert "run_id" in data
    assert "findings" in data
    assert data["release_blocking_count"] == 0
