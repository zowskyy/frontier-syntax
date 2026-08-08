"""Tests for plugin lifecycle (SLICE 19)."""

from __future__ import annotations

from pathlib import Path

import pytest

from local_agent.plugins.lifecycle import PluginLifecycle
from local_agent.plugins.supervisor import PluginManifestError


def test_discover_plugins(project_root: Path) -> None:
    lifecycle = PluginLifecycle()
    discovered = lifecycle.discover([project_root / "plugins"])
    assert len(discovered) >= 1
    names = [p.name for p in discovered]
    assert "example-echo" in names


def test_invalid_manifest_rejected(tmp_path: Path) -> None:
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "manifest.json").write_text("{}", encoding="utf-8")
    lifecycle = PluginLifecycle()
    discovered = lifecycle.discover([tmp_path])
    assert len(discovered) == 0


def test_start_health_shutdown(project_root: Path) -> None:
    lifecycle = PluginLifecycle()
    lifecycle.discover([project_root / "plugins"])
    proc = lifecycle.start("example-echo")
    assert proc.alive
    assert lifecycle.health_check("example-echo")
    lifecycle.shutdown("example-echo")
    assert lifecycle.state.plugins["example-echo"].status == "stopped"


def test_duplicate_tool_rejection(tmp_path: Path) -> None:
    for name in ("plugin_a", "plugin_b"):
        pdir = tmp_path / name
        pdir.mkdir()
        (pdir / "manifest.json").write_text(
            f'{{"name": "{name}", "version": "1.0.0", "entrypoint": "x.py", "permissions": ["shared_tool"]}}',
            encoding="utf-8",
        )
        (pdir / "x.py").write_text("import sys\nsys.exit(0)", encoding="utf-8")

    lifecycle = PluginLifecycle()
    lifecycle.discover([tmp_path])
    lifecycle.start("plugin_a")
    with pytest.raises(PluginManifestError, match="Duplicate tool"):
        lifecycle.start("plugin_b")
    lifecycle.shutdown_all()


def test_reload_no_token_leak(project_root: Path) -> None:
    lifecycle = PluginLifecycle()
    lifecycle.discover([project_root / "plugins"])
    lifecycle.start("example-echo")
    old_token = lifecycle._running["example-echo"].capability_token.token
    lifecycle.reload("example-echo")
    assert not lifecycle.supervisor.is_token_active(old_token)
    lifecycle.shutdown_all()


def test_list_plugins(project_root: Path) -> None:
    lifecycle = PluginLifecycle()
    lifecycle.discover([project_root / "plugins"])
    plugins = lifecycle.list_plugins()
    assert any(p["name"] == "example-echo" for p in plugins)
