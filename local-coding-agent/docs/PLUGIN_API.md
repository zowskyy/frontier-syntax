# Plugin API

Plugins run in isolated subprocesses with capability tokens (SLICE 18–19).

## Manifest (`plugins/example/manifest.json`)

```json
{
  "name": "echo",
  "version": "0.1.0",
  "api_version": "1",
  "entrypoint": "echo_plugin.py",
  "permissions": ["echo"]
}
```

## IPC

JSON-RPC over stdin/stdout. The supervisor grants only declared permissions.

## Lifecycle

`PluginLifecycle` handles discovery, validation, health, reload, and shutdown.
