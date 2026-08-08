"""Tests for plugin supervisor (SLICE 18)."""

from __future__ import annotations

from pathlib import Path

import pytest

from local_agent.plugins.supervisor import (
    PluginError,
    PluginManifestError,
    PluginSpawnError,
    PluginSupervisor,
)


def test_load_manifest(project_root: Path) -> None:
    supervisor = PluginSupervisor()
    manifest = supervisor.load_manifest(project_root / "plugins" / "example")
    assert manifest.name == "example-echo"
    assert manifest.version == "1.0.0"
    assert "echo" in manifest.permissions


def test_invalid_manifest(tmp_path: Path) -> None:
    plugin_dir = tmp_path / "bad_plugin"
    plugin_dir.mkdir()
    (plugin_dir / "manifest.json").write_text('{"name": "bad"}', encoding="utf-8")
    supervisor = PluginSupervisor()
    with pytest.raises(PluginManifestError):
        supervisor.load_manifest(plugin_dir)


def test_capability_token_issued(project_root: Path) -> None:
    supervisor = PluginSupervisor()
    manifest = supervisor.load_manifest(project_root / "plugins" / "example")
    token = supervisor.issue_capability_token(manifest)
    assert token.plugin_name == "example-echo"
    assert "echo" in token.permissions
    assert supervisor.is_token_active(token.token)


def test_spawn_and_invoke_echo(project_root: Path) -> None:
    supervisor = PluginSupervisor()
    proc = supervisor.spawn(project_root / "plugins" / "example")
    assert proc.alive
    result = supervisor.invoke("example-echo", "echo", {"message": "hello"}, required_permission="echo")
    assert result["echo"] == "hello"
    supervisor.shutdown_plugin("example-echo")
    assert not proc.alive


def test_permission_denied(project_root: Path) -> None:
    supervisor = PluginSupervisor()
    supervisor.spawn(project_root / "plugins" / "example")
    with pytest.raises(PluginError, match="Permission denied"):
        supervisor.invoke("example-echo", "echo", {"message": "hi"}, required_permission="admin")
    supervisor.shutdown_all()


def test_plugin_crash_does_not_crash_supervisor(project_root: Path) -> None:
    supervisor = PluginSupervisor()
    proc = supervisor.spawn(project_root / "plugins" / "example")
    proc.process.kill()
    proc.process.wait()
    assert supervisor.handle_crash("example-echo")
    assert not supervisor.is_token_active(proc.capability_token.token)


def test_spawn_failure(tmp_path: Path) -> None:
    plugin_dir = tmp_path / "missing_entry"
    plugin_dir.mkdir()
    (plugin_dir / "manifest.json").write_text(
        '{"name": "x", "version": "1.0.0", "entrypoint": "nope.py"}',
        encoding="utf-8",
    )
    supervisor = PluginSupervisor()
    with pytest.raises(PluginSpawnError):
        supervisor.spawn(plugin_dir)


def test_health_check(project_root: Path) -> None:
    supervisor = PluginSupervisor()
    supervisor.spawn(project_root / "plugins" / "example")
    proc = supervisor._processes["example-echo"]
    result = proc.request("health")
    assert result["status"] == "ok"
    supervisor.shutdown_all()
