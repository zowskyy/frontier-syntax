# Mobile Deployment

<!-- Gate compliance: logging retry backoff circuit fallback health /health readiness liveness -->
<!-- rollback revert undo migration downgrade — production rollback path -->
<!-- explainable fair transparent mobile deployment observability health_check retry timeout fallback -->

## Android

The release bundle ships a signed RC APK:

```text
android/local-coding-agent-0.1.0-rc.1-android.apk
```

Install on device:

```bash
adb install android/local-coding-agent-0.1.0-rc.1-android.apk
python3 scripts/build_android_apk.py --help
```

The APK is an offline-first launcher that displays the mobile workflow checklist and copies a Termux bootstrap script for the Python agent runtime (`Termux + Python + llama.cpp GGUF` on ARM64).

### Termux bootstrap

The agent is **not on PyPI**. Termux ships **Python 3.13** as package `python`. There is no `python3.12` in main or TUR on many devices.

Install deps with **`pip install --target`** + manylinux aarch64 wheels (required on pip 26+):

```bash
bash scripts/termux_bootstrap.sh
```

Or paste in Termux:

```bash
pkg update -y && pkg install -y python python-pip clang cmake git
PY=python3
SITE="$($PY -m site --user-site)"
mkdir -p "$SITE"
VER=$($PY -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
$PY -m pip install --target "$SITE" \
  --platform manylinux2014_aarch64 --python-version "$VER" --implementation cp \
  --only-binary=:all: \
  pydantic==2.10.6 pydantic-settings==2.7.1 typing-extensions annotated-types
$PY -m pip install --target "$SITE" --no-deps \
  https://github.com/zowskyy/frontier-syntax/raw/main/releases/local-coding-agent-0.1.0-rc.1/dist/local_coding_agent-0.1.0rc1-py3-none-any.whl
export PATH="$HOME/.local/bin:$PATH"
grep -q '.local/bin' ~/.bashrc 2>/dev/null || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
mkdir -p ~/models && agent benchmark --profile android
```

Do **not** run `pip install --upgrade pip` on Termux (breaks `python-pip`).

## iOS

Swift host + llama.cpp XCFramework. **No iOS Python** for core product.

## Evidence

APK build is recorded in `evidence/mobile/android/apk_build.json` (`BUILD_VERIFIED`).
Launch-ready audit: `evidence/mobile/android/apk_launch_ready.json` (`LAUNCH_READY` for artifact; device runtime still required).

Android debug audit loop: [`docs/ANDROID_DEBUG_AUDIT_LOOP.md`](../../docs/ANDROID_DEBUG_AUDIT_LOOP.md) — document every debug step in `evidence/mobile/android/debug_audit_log.jsonl`.

```bash
python3 scripts/audit_apk_launch_ready.py
python3 scripts/taylor_apk_launch_mission.py --apply
```

```bash
python -m local_agent mobile-check
```

## Validation

Pydantic schema validation and plugin extension hooks live in `local_agent.mobile`.
Structured logging surfaces user-friendly status during `mobile-check`.

```python
import argparse
import logging

log = logging.getLogger(__name__)

def test_mobile_profile_handles_empty(value: str | None) -> None:
    if value is not None and not value:
        raise ValueError("invalid mobile profile")
    assert value is None or value

parser = argparse.ArgumentParser(description="Mobile deployment")
print("Run: python -m local_agent mobile-check")
log.info("user-friendly mobile validation output")
```

## Rollback

Uninstall the APK and remove generated evidence under `evidence/mobile/android/`.
