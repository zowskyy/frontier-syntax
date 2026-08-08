"""Plugin lifecycle: discovery, validation, health, shutdown."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from local_agent.plugins.supervisor import (
    PluginError,
    PluginManifest,
    PluginManifestError,
    PluginProcess,
    PluginSpawnError,
    PluginSupervisor,
)

logger = logging.getLogger(__name__)


@dataclass
class PluginInfo:
    name: str
    version: str
    path: Path
    manifest: PluginManifest
    status: str = "discovered"
    health: str = "unknown"


@dataclass
class LifecycleState:
    plugins: dict[str, PluginInfo] = field(default_factory=dict)
    tool_names: dict[str, str] = field(default_factory=dict)


class PluginLifecycle:
    """Manages plugin discovery, validation, health polling, and shutdown."""

    def __init__(self, supervisor: PluginSupervisor | None = None) -> None:
        self.supervisor = supervisor or PluginSupervisor()
        self.state = LifecycleState()
        self._running: dict[str, PluginProcess] = {}

    def discover(self, plugin_dirs: list[str | Path]) -> list[PluginInfo]:
        discovered: list[PluginInfo] = []
        for directory in plugin_dirs:
            base = Path(directory)
            if not base.exists():
                continue
            for candidate in sorted(base.iterdir()):
                if not candidate.is_dir():
                    continue
                manifest_path = candidate / "manifest.json"
                if not manifest_path.exists():
                    continue
                try:
                    manifest = self.supervisor.load_manifest(candidate)
                    info = PluginInfo(
                        name=manifest.name,
                        version=manifest.version,
                        path=candidate,
                        manifest=manifest,
                    )
                    discovered.append(info)
                    self.state.plugins[manifest.name] = info
                except PluginManifestError as exc:
                    logger.warning("Rejected plugin at %s: %s", candidate, exc)
        return discovered

    def validate(self, info: PluginInfo) -> None:
        if not info.manifest.name:
            raise PluginManifestError("Plugin name cannot be empty")
        entrypoint = info.path / info.manifest.entrypoint
        if not entrypoint.exists():
            raise PluginManifestError(f"Entrypoint missing: {entrypoint}")
        for tool in info.manifest.permissions:
            if tool in self.state.tool_names and self.state.tool_names[tool] != info.name:
                raise PluginManifestError(
                    f"Duplicate tool name '{tool}' from {self.state.tool_names[tool]}"
                )

    def start(self, plugin_name: str) -> PluginProcess:
        info = self.state.plugins.get(plugin_name)
        if not info:
            raise PluginError(f"Unknown plugin: {plugin_name}")
        self.validate(info)
        for perm in info.manifest.permissions:
            self.state.tool_names[perm] = plugin_name
        try:
            proc = self.supervisor.spawn(info.path)
            self._running[plugin_name] = proc
            info.status = "running"
            return proc
        except PluginSpawnError:
            info.status = "failed"
            raise

    def health_check(self, plugin_name: str, timeout: float = 2.0) -> bool:
        proc = self._running.get(plugin_name)
        if not proc or not proc.alive:
            info = self.state.plugins.get(plugin_name)
            if info:
                info.health = "dead"
            return False
        try:
            result = proc.request("health", timeout=timeout)
            healthy = result.get("status") == "ok"
            info = self.state.plugins[plugin_name]
            info.health = "ok" if healthy else "unhealthy"
            return healthy
        except PluginError:
            info = self.state.plugins[plugin_name]
            info.health = "unhealthy"
            self.supervisor.handle_crash(plugin_name)
            self._running.pop(plugin_name, None)
            info.status = "crashed"
            return False

    def poll_health(self, interval: float = 1.0, duration: float = 3.0) -> dict[str, bool]:
        results: dict[str, bool] = {}
        deadline = time.monotonic() + duration
        while time.monotonic() < deadline:
            for name in list(self._running.keys()):
                results[name] = self.health_check(name)
            time.sleep(interval)
        return results

    def reload(self, plugin_name: str) -> PluginProcess:
        old_proc = self._running.get(plugin_name)
        old_token = old_proc.capability_token.token if old_proc else None
        self.shutdown(plugin_name)
        if old_token and self.supervisor.is_token_active(old_token):
            raise PluginError("Capability token leaked after reload")
        return self.start(plugin_name)

    def shutdown(self, plugin_name: str, timeout: float = 3.0) -> None:
        self.supervisor.shutdown_plugin(plugin_name, timeout=timeout)
        self._running.pop(plugin_name, None)
        info = self.state.plugins.get(plugin_name)
        if info:
            info.status = "stopped"
            info.health = "unknown"
        for tool, owner in list(self.state.tool_names.items()):
            if owner == plugin_name:
                del self.state.tool_names[tool]

    def shutdown_all(self, timeout: float = 3.0) -> None:
        for name in list(self._running.keys()):
            self.shutdown(name, timeout=timeout)

    def list_plugins(self) -> list[dict[str, Any]]:
        return [
            {
                "name": info.name,
                "version": info.version,
                "status": info.status,
                "health": info.health,
                "permissions": info.manifest.permissions,
            }
            for info in self.state.plugins.values()
        ]
