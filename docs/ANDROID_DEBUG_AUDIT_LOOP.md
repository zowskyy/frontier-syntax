# Android Debug Audit Loop

Global policy for debugging Android apps in this repo and all Cursor sessions.
Canonical sources:

- [Android Developer Fundamentals (V2) — Concepts](https://google-developer-training.github.io/android-developer-fundamentals-course-concepts-v2/)
- [Debug your app — Android Developers](https://developer.android.com/studio/debug)
- Project rule: `.cursor/rules/android-debug-audit-loop.mdc`

---

## Purpose

An **audit loop** is a disciplined cycle of **record → change → run → analyze → repeat** until the root cause is found and verified fixed. It prevents missing subtle triggers (layout overflow, permissions, build variant) and makes issues reproducible.

**Lesson learned (2026-08-09):** Lengthening `termux_bootstrap.sh` pushed the copy button below the fold because `activity_main.xml` had no `ScrollView` and no pinned bottom action. Static APK checks passed; the user found the UI bug. This document exists so that cannot happen again without failing CI.

---

## Core audit loop rules

### 1. Document every action and outcome

Before and during debugging, write down:

- What you did (code change, log filter, UI tap)
- The **order** of steps
- The **result** (success, crash, unexpected behavior)

**Repo sink:** append JSON lines to `evidence/mobile/android/debug_audit_log.jsonl`:

```json
{"ts":"2026-08-09T01:30:00Z","action":"changed termux_bootstrap.sh","step":3,"result":"rebuilt APK","device":null,"notes":"+12 lines pydantic install"}
```

### 2. Start with the smallest change

Change **one** variable at a time (one flag, one permission, one layout attribute). Re-run. This isolates cause.

### 3. Check all details

Log conditions that affect Android behavior:

| Factor | Example |
|--------|---------|
| Device / emulator | Pixel 6, API 34 |
| Screen size | 1080×2400, smallest width dp |
| Permissions | INTERNET, storage |
| Build variant | release vs debug |
| Network | offline-first APK |
| Asset size | bootstrap script line count |

### 4. Use Android Studio / platform tools effectively

From [Android Studio debugging](https://developer.android.com/studio/debug):

| Tool | Use |
|------|-----|
| **Debugger** | Breakpoints in Kotlin/Java; Step Into/Over/Out; variables & watches; call stack |
| **Logcat** | Filter by package; capture before/after each change |
| **Layout Inspector** | Live UI hierarchy; verify buttons visible, not clipped |
| **Network Profiler** | API calls (if applicable) |
| **ADB** | Install, logcat, shell inspection |
| **Chrome DevTools** | WebView debugging (if applicable) |

When no device is attached (cloud agent): **read layout XML** and correlate asset length with scroll/pin constraints.

### 5. Reproduce consistently

Use the same APK SHA, device profile, and install path each run. Intermittent bugs → multiple runs, record variance.

### 6. Correlate symptoms with timestamps

Align user reports, Logcat, and audit log entries by time to see what preceded the failure.

### 7. Review and close the loop

After a fix:

1. Re-run `python3 scripts/audit_apk_launch_ready.py`
2. Confirm **APK-008** (scroll + pinned copy) passes
3. On device/emulator if available: open app → verify copy button visible without hunting
4. Update `MOBILE.md` / incident docs if policy changed
5. Mark loop **closed** in debug audit log

---

## Example loop (copy button missing)

| Step | Action | Outcome |
|------|--------|---------|
| 1 | User: no copy option at bottom | Report received |
| 2 | Read `activity_main.xml` | No ScrollView; button below long `bootstrapText` |
| 3 | Read `termux_bootstrap.sh` | 33 lines ( grew after pydantic fix ) |
| 4 | Change layout: ScrollView + pin button to bottom | Layout updated |
| 5 | Rebuild APK, audit | LAUNCH_READY + APK-008 pass |
| 6 | Document | This file + APK-008 check |

---

## Automated checks (CI / cloud agent)

```bash
python3 scripts/audit_apk_launch_ready.py
python3 scripts/apk_launch_checks.py
```

| Check | What it enforces |
|-------|------------------|
| APK-001–007 | Artifact, SHA, badging, permissions, release bundle |
| **APK-008** | `ScrollView` present; `copyBootstrapButton` pinned to bottom **outside** scroll |

Static checks do **not** replace device verification. Evidence field `device_runtime` remains `UNEXECUTED_REQUIRES_RUNTIME` until a human or emulator run is recorded.

---

## Agent obligations

1. Never claim mobile UI is fixed without APK-008 pass **and** layout review when assets/layouts changed.
2. Cite user screenshots under **Visual evidence** (see `visual-evidence-audit.mdc`).
3. Run full audit-debug loop (see `audit-debug-loop.mdc`) — no iteration cap.
4. Prefer pinned primary actions for copy/install flows on small screens.

---

## References

- [Android Developer Fundamentals V2](https://google-developer-training.github.io/android-developer-fundamentals-course-concepts-v2/)
- [Debug your app](https://developer.android.com/studio/debug)
- [Layout Inspector](https://developer.android.com/studio/debug/layout-inspector)
- [Logcat](https://developer.android.com/studio/debug/logcat)
- [Analyze a stack trace](https://developer.android.com/studio/debug/stack-traces)
