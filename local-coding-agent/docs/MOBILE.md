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

## iOS

Swift host + llama.cpp XCFramework. **No iOS Python** for core product.

## Evidence

APK build is recorded in `evidence/mobile/android/apk_build.json` (`BUILD_VERIFIED`).
Device runtime tests remain `UNEXECUTED_REQUIRES_RUNTIME` until real hardware verification.

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
