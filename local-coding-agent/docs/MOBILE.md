# Mobile Deployment

## Android

Termux + Python control layer + llama.cpp GGUF (ARM64).

## iOS

Swift host + llama.cpp XCFramework. **No iOS Python** for core product.

## Evidence

Device runtime tests are `UNEXECUTED_REQUIRES_RUNTIME` until real hardware verification.

Run scaffold evidence:

```bash
python -m local_agent mobile-check
```
