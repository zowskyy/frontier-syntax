"""Plugin supervisor for subprocess-isolated plugins."""

from __future__ import annotations

import json
import logging
import secrets
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class PluginError(Exception):
    """Base plugin error."""


class PluginManifestError(PluginError):
    """Invalid plugin manifest."""


class PluginSpawnError(PluginError):
    """Failed to spawn plugin subprocess."""


@dataclass
class PluginManifest:
    name: str
    version: str
    entrypoint: str
    permissions: list[str] = field(default_factory=list)
    description: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PluginManifest:
        required = ("name", "version", "entrypoint")
        for key in required:
            if key not in data:
                raise PluginManifestError(f"Missing required field: {key}")
        permissions = data.get("permissions", [])
        if not isinstance(permissions, list):
            raise PluginManifestError("permissions must be a list")
        return cls(
            name=data["name"],
            version=data["version"],
            entrypoint=data["entrypoint"],
            permissions=permissions,
            description=data.get("description", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "entrypoint": self.entrypoint,
            "permissions": self.permissions,
            "description": self.description,
        }


@dataclass
class CapabilityToken:
    token: str
    plugin_name: str
    permissions: list[str]
    issued_at: float = field(default_factory=time.time)

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions


@dataclass
class PluginProcess:
    manifest: PluginManifest
    process: subprocess.Popen[str]
    capability_token: CapabilityToken
    plugin_dir: Path

    @property
    def alive(self) -> bool:
        return self.process.poll() is None

    def request(self, method: str, params: dict[str, Any] | None = None, timeout: float = 5.0) -> dict[str, Any]:
        if not self.alive:
            raise PluginError("Plugin process is not running")
        req = {"jsonrpc": "2.0", "id": secrets.token_hex(4), "method": method, "params": params or {}}
        self.process.stdin.write(json.dumps(req) + "\n")
        self.process.stdin.flush()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            line = self.process.stdout.readline()
            if not line:
                time.sleep(0.01)
                continue
            resp = json.loads(line)
            if resp.get("id") == req["id"]:
                if "error" in resp:
                    raise PluginError(resp["error"].get("message", "Plugin error"))
                return resp.get("result", {})
        raise PluginError(f"Plugin request timed out: {method}")

    def shutdown(self, timeout: float = 3.0) -> None:
        if not self.alive:
            return
        try:
            self.request("shutdown", timeout=timeout)
        except PluginError:
            pass
        try:
            self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=1.0)


class PluginSupervisor:
    """Spawns and manages subprocess plugins with capability tokens."""

    def __init__(self) -> None:
        self._active_tokens: dict[str, CapabilityToken] = {}
        self._processes: dict[str, PluginProcess] = {}

    def load_manifest(self, plugin_dir: str | Path) -> PluginManifest:
        manifest_path = Path(plugin_dir) / "manifest.json"
        if not manifest_path.exists():
            raise PluginManifestError(f"No manifest.json in {plugin_dir}")
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return PluginManifest.from_dict(data)

    def issue_capability_token(self, manifest: PluginManifest) -> CapabilityToken:
        token = CapabilityToken(
            token=secrets.token_urlsafe(32),
            plugin_name=manifest.name,
            permissions=list(manifest.permissions),
        )
        self._active_tokens[token.token] = token
        return token

    def spawn(self, plugin_dir: str | Path) -> PluginProcess:
        plugin_path = Path(plugin_dir)
        manifest = self.load_manifest(plugin_path)
        token = self.issue_capability_token(manifest)
        entrypoint = plugin_path / manifest.entrypoint
        if not entrypoint.exists():
            raise PluginSpawnError(f"Entrypoint not found: {entrypoint}")

        env = {
            "PLUGIN_CAPABILITY_TOKEN": token.token,
            "PLUGIN_PERMISSIONS": json.dumps(token.permissions),
            "PYTHONUNBUFFERED": "1",
        }
        try:
            process = subprocess.Popen(
                [sys.executable, str(entrypoint)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(plugin_path),
                env={**dict(__import__("os").environ), **env},
            )
        except OSError as exc:
            logger.error("Failed to spawn plugin %s: %s", manifest.name, exc)
            raise PluginSpawnError(f"Spawn failed: {exc}") from exc

        plugin_proc = PluginProcess(
            manifest=manifest,
            process=process,
            capability_token=token,
            plugin_dir=plugin_path,
        )
        self._processes[manifest.name] = plugin_proc
        return plugin_proc

    def invoke(
        self,
        plugin_name: str,
        method: str,
        params: dict[str, Any] | None = None,
        required_permission: str | None = None,
    ) -> dict[str, Any]:
        proc = self._processes.get(plugin_name)
        if not proc:
            raise PluginError(f"Plugin not running: {plugin_name}")
        if required_permission and not proc.capability_token.has_permission(required_permission):
            raise PluginError(f"Permission denied: {required_permission}")
        try:
            return proc.request(method, params)
        except PluginError:
            if not proc.alive:
                logger.warning("Plugin %s crashed during invocation", plugin_name)
            raise

    def shutdown_plugin(self, plugin_name: str, timeout: float = 3.0) -> None:
        proc = self._processes.pop(plugin_name, None)
        if proc:
            token = proc.capability_token.token
            self._active_tokens.pop(token, None)
            proc.shutdown(timeout=timeout)

    def shutdown_all(self, timeout: float = 3.0) -> None:
        for name in list(self._processes.keys()):
            self.shutdown_plugin(name, timeout=timeout)

    def is_token_active(self, token: str) -> bool:
        return token in self._active_tokens

    def handle_crash(self, plugin_name: str) -> bool:
        """Handle plugin crash without affecting agent core. Returns True if crashed."""
        proc = self._processes.get(plugin_name)
        if proc and not proc.alive:
            logger.error("Plugin %s crashed with code %s", plugin_name, proc.process.returncode)
            self.shutdown_plugin(plugin_name)
            return True
        return False
