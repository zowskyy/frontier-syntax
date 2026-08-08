# Threat Model

Trust levels T0–T5 per blueprint. Policy engine sits between model output (T3) and privileged operations.

Default policy: READ within workspace; WRITE transactional; NETWORK disabled; PLUGIN subprocess only.

See `SECURITY.md` and `src/local_agent/security/harness.py` for adversarial regression fixtures.
