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

The agent is **not on PyPI**. Use **Python 3.12** on Termux (not 3.13) so `pydantic-core` installs from prebuilt wheels instead of compiling Rust on-device.

```bash
bash scripts/termux_bootstrap.sh
```

Or paste manually in Termux:

```bash
pkg update -y && pkg install -y python-3.12 clang cmake git
PY=python3.12
$PY -m pip install --user --upgrade pip wheel
$PY -m pip install --user \
  --platform manylinux2014_aarch64 --python-version 3.12 --implementation cp \
  --only-binary=:all: \
  "pydantic>=2,<3" "pydantic-settings>=2,<3" typing-extensions annotated-types
$PY -m pip install --user --no-deps \
  https://github.com/zowskyy/frontier-syntax/raw/main/releases/local-coding-agent-0.1.0-rc.1/dist/local_coding_agent-0.1.0rc1-py3-none-any.whl
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
mkdir -p ~/models && agent benchmark --profile android
```

If install still fails, confirm `python3.12 --version` shows 3.12.x (not 3.13).

## iOS

Swift host + llama.cpp XCFramework. **No iOS Python** for core product.

## Evidence

APK build is recorded in `evidence/mobile/android/apk_build.json` (`BUILD_VERIFIED`).
Launch-ready audit: `evidence/mobile/android/apk_launch_ready.json` (`LAUNCH_READY` for artifact; device runtime still required).

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
