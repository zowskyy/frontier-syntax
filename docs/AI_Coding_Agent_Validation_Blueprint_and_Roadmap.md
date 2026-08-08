# Local-First AI Coding Agent — Validation Audit ×3 → Implementability Review ×3 → Slice Blueprint → Release Roadmap

| Field | Value |
|-------|-------|
| **Document status** | Engineering deliverable |
| **Review date** | 2026-08-08 |
| **Frontier spec** | `frontier/roadmap/local_coding_agent.fr` |
| **Tracking manifest** | `manifest/local_coding_agent_tracking.json` |
| **Slice count** | 37 (SLICE 0–36) |
| **Release phases** | 9 (Phase 0–8) |
| **Go decision allowed** | **No** |

---

## Table of Contents

1. [Executive Decision](#1-executive-decision)
2. [Source Roadmap Assessment](#2-source-roadmap-assessment-13-original-phases)
3. [Verification Status Vocabulary](#3-verification-status-vocabulary)
4. [Audit 1 — Requirements and Evidence](#4-audit-1--requirements-and-evidence)
5. [Audit 1 — Security Findings](#5-audit-1--security-findings)
6. [Audit 1 — Reliability Invariants](#6-audit-1--reliability-invariants)
7. [Audit 1 — Performance Findings](#7-audit-1--performance-findings)
8. [Audit 2 — Architecture and Threat Model](#8-audit-2--architecture-and-threat-model)
9. [Audit 2 — Tool Risk Classes and Default Policy](#9-audit-2--tool-risk-classes-and-default-policy)
10. [Audit 2 — Knowledge Security](#10-audit-2--knowledge-security)
11. [Audit 3 — Implementation Feasibility](#11-audit-3--implementation-feasibility-gaps-and-corrections)
12. [Audit 3 — SQLite Data Model](#12-audit-3--sqlite-data-model)
13. [Audit 3 — Agent State Machine](#13-audit-3--agent-state-machine)
14. [Audit 3 — Edit Protocol](#14-audit-3--edit-protocol)
15. [Audit 3 — Final Findings](#15-audit-3--final-findings)
16. [Slice-by-Slice Blueprint](#16-slice-by-slice-blueprint-slice-0--slice-36)
17. [Three-Pass Implementability Review](#17-three-pass-implementability-review)
18. [Final Acceptance Matrix](#18-final-acceptance-matrix)
19. [Release Roadmap Phase 0–8](#19-release-roadmap-phase-0-8)
20. [Evidence Package Structure](#20-evidence-package-structure)
21. [Evidence Record Format](#21-evidence-record-format)
22. [Current Web Evidence Used](#22-current-web-evidence-used)
23. [Final Engineering Verdict](#23-final-engineering-verdict)
24. [Implementation Rule Pipeline](#24-implementation-rule-pipeline)
25. [Public Release Gate](#25-public-release-gate)

---

## 1. Executive Decision

**Review date:** 2026-08-08

**Verdict:** Do not implement the source roadmap literally. Build a **model-agnostic local-first coding agent** with **deterministic capability enforcement** outside the model.

### 1.1 Architectural Corrections (Mandatory)

| Decision | Status | Rationale |
|----------|--------|-----------|
| Reject fixed **Qwen3-Coder-7B** as sole model | **REJECTED** | Public Ollama/library listings expose Qwen3-Coder **30B** and larger variants; **7B coding variant not verified** as specified |
| **Model provider abstraction** | **REQUIRED** | Ollama, llama.cpp, and Mock providers must be interchangeable via configuration |
| **Policy engine outside model** | **REQUIRED** | Model output is untrusted (T3); every privileged action requires deterministic authorization |
| **SQLite authoritative state** | **REQUIRED** | Documents, chunks, tasks, events, checkpoints live in SQLite; Chroma is optional overlay |
| **FTS5 fallback** | **REQUIRED** | Lexical search must work with zero embedding/Chroma dependency |
| **Subprocess plugins** | **REQUIRED** | Same-process plugin code is T4 untrusted; isolate via subprocess + capability tokens |
| **Transactional edits** | **REQUIRED** | Hash-checked, temp-copy, syntax-verify, atomic commit; no direct overwrite |
| **Safe checkpoints** | **REQUIRED** | SQLite + JSON + checksums + schema versioning; **no pickle deserialization** |
| **Explicit network policy** | **REQUIRED** | Network disabled by default; SSRF controls when enabled |
| Runtime tests claimed passed | **NOT VERIFIED** | No independent execution evidence for claimed runtime test pass at audit time |

### 1.2 Executive Decision Record

```json
{
  "review_date": "2026-08-08",
  "verdict": "model-agnostic local-first agent with deterministic capability enforcement",
  "reject_fixed_qwen3_coder_7b": true,
  "require_model_provider_abstraction": true,
  "require_policy_engine_outside_model": true,
  "require_sqlite_authoritative_state": true,
  "require_fts5_fallback": true,
  "require_subprocess_plugins": true,
  "require_transactional_edits": true,
  "require_safe_checkpoints": true,
  "require_explicit_network_policy": true,
  "runtime_tests_claimed_passed": false
}
```

### 1.3 What We Build Instead

The corrected product is a **local-first AI coding agent** that:

1. Runs inference via **pluggable providers** (Ollama for desktop, llama.cpp for mobile/offline).
2. Indexes project knowledge in **SQLite + FTS5**, with optional Chroma for semantic search.
3. Executes tools only through a **policy engine** that the model cannot bypass.
4. Applies code changes through a **transactional edit protocol**.
5. Recovers from failures via **validated checkpoints** (never pickle).
6. Extends capability via **subprocess plugins** with explicit capability tokens.
7. Ships only when **executable evidence** exists for every slice acceptance criterion.

---

## 2. Source Roadmap Assessment (13 Original Phases)

The user-supplied 13-phase validation roadmap was assessed against current public evidence and engineering feasibility. **None of the 13 phases may be executed as originally written** without the corrections in Section 1.

| Original Phase | Name | Mapped Slices | Assessment |
|----------------|------|---------------|------------|
| 1 | Dependency Verification | 1, 4, 12, 13 | **REWRITE** — Qwen3-Coder-7B invalid; use model matrix |
| 2 | Security Audit | 2, 7, 22, 30 | **ACCEPT** with added capability auth and SSRF controls |
| 3 | Reliability Testing | 21, 23 | **ACCEPT** with 10 invariants (Section 6) |
| 4 | Performance Benchmarking | 25, 29, 31 | **REWRITE** — device/model profiles, not fixed thresholds |
| 5 | Knowledge Augmentation Validation | 24 | **ACCEPT** with FTS5 baseline requirement |
| 6 | Qwen-Specific Behavior Testing | 25 | **REWRITE** — per-model matrix, not single Qwen SKU |
| 7 | Plugin System Validation | 18, 19 | **REWRITE** — subprocess boundary mandatory |
| 8 | Mobile Deployment Testing | 27, 28, 29, 30 | **ACCEPT** with iOS native path (no Python) |
| 9 | Knowledge Ingestion Pipeline | 10, 11, 14, 15 | **REWRITE** — SQLite authoritative, Chroma optional |
| 10 | End-to-End Integration Testing | 26 | **ACCEPT** with evidence-based acceptance |
| 11 | Checkpoint and Recovery | 20, 21 | **REWRITE** — no pickle; validated state only |
| 12 | Documentation and Release Preparation | 32, 33 | **ACCEPT** |
| 13 | Public Release Checklist | 34, 35, 36 | **ACCEPT** with six public-release checks (Section 25) |

### 2.1 Gap Summary

| Gap ID | Original assumption | Corrected requirement |
|--------|---------------------|----------------------|
| GAP-001 | Single model: Qwen3-Coder-7B | Model compatibility matrix with verified SKUs |
| GAP-002 | Chroma as primary store | SQLite authoritative; Chroma replaceable |
| GAP-003 | Plugins in same process | Subprocess + capability tokens |
| GAP-004 | Direct file overwrite | Transactional hash-checked edits |
| GAP-005 | Pickle checkpoints | JSON/SQLite + checksum + schema version |
| GAP-006 | Universal performance thresholds | Per device/model profiles |
| GAP-007 | Python on iOS | Swift + llama.cpp XCFramework |
| GAP-008 | Model output executes tools | Policy engine gate on every tool call |
| GAP-009 | Retrieved docs trusted | T2 untrusted; cannot grant authority |
| GAP-010 | Network fetch unrestricted | Explicit capability + SSRF controls |

---

## 3. Verification Status Vocabulary

All audits, slices, and release checks use this vocabulary consistently.

| Status | Meaning | Use when |
|--------|---------|----------|
| `VERIFIED` | Claim supported by reproducible evidence or authoritative public source | Dependency exists, API documented, build tested |
| `PARTIALLY_VERIFIED` | Claim partially true; conditions or scope limits apply | Mobile Python on Android only; model exists but not exact SKU |
| `UNVERIFIED` | No evidence collected yet; claim not disproven | Security advisory scan not run |
| `INVALID_AS_WRITTEN` | Claim false or infeasible as specified | Qwen3-Coder-7B as named dependency |
| `REPLACED` | Component superseded by corrected architecture | Chroma as sole knowledge store |
| `UNEXECUTED_REQUIRES_RUNTIME` | Correct design but no runtime execution evidence | Slice acceptance, device tests |

**Rule:** `VERIFIED` and `PARTIALLY_VERIFIED` require a citation in Section 22 or an evidence record in the evidence package. `UNEXECUTED_REQUIRES_RUNTIME` is the default gate status for all slices until implementation completes.

---

## 4. Audit 1 — Requirements and Evidence

**Audit scope:** Dependency verification, public evidence cross-check, feasibility of stated requirements.

### 4.1 Dependency Matrix

| Component | Status | Evidence summary | Required change |
|-----------|--------|------------------|-----------------|
| **Qwen3-Coder-7B** | `INVALID_AS_WRITTEN` | Ollama library lists Qwen3-Coder 30B/480B-class models; 7B coding SKU not verified as specified | Replace with model compatibility matrix |
| **Ollama** | `VERIFIED` | Active project; local HTTP API; multi-model support | Use as provider, never sole abstraction |
| **ChromaDB** | `REPLACED` | Package available (`VERIFIED` for existence) | Architecture: optional semantic layer; SQLite authoritative; FTS5 fallback |
| **nomic-embed-text** | `VERIFIED` | Available via Ollama; documented dimensions | Configurable embedding; persist model_id, revision, dimension, chunking |
| **llama.cpp** | `VERIFIED` | GGUF inference; Android ARM64 builds; iOS XCFramework path | Direct inference portability layer |
| **Python on mobile** | `PARTIALLY_VERIFIED` | Android Termux route viable | iOS: Swift + llama.cpp — **no iOS Python dependency** |

### 4.2 Model Compatibility Matrix

| Profile | Candidate | Primary purpose | Status |
|---------|-----------|-----------------|--------|
| `small_mobile` | Verified GGUF coding model (profile-specific) | Phones, low RAM | `UNVERIFIED` — must be selected per device evidence |
| `medium_local` | Qwen3-Coder 30B (or equivalent) | Desktop agent | `VERIFIED` via Ollama |
| `next_generation` | Qwen3-Coder next / 480B-class | Desktop high performance | `PARTIALLY_VERIFIED` — hardware dependent |
| `direct_inference` | llama.cpp + GGUF | Mobile offline | `VERIFIED` |

### 4.3 Requirements Traceability

| Requirement ID | Requirement | Evidence status |
|----------------|-------------|-----------------|
| REQ-001 | Local inference without cloud dependency | `VERIFIED` (Ollama + llama.cpp) |
| REQ-002 | Project-aware code retrieval | `PARTIALLY_VERIFIED` (architecture defined; not implemented) |
| REQ-003 | Safe automated edits | `UNEXECUTED_REQUIRES_RUNTIME` |
| REQ-004 | Plugin extensibility | `PARTIALLY_VERIFIED` (subprocess design) |
| REQ-005 | Mobile offline operation | `PARTIALLY_VERIFIED` (llama.cpp paths) |
| REQ-006 | Recovery after crash | `UNEXECUTED_REQUIRES_RUNTIME` |
| REQ-007 | Security adversarial suite | `UNEXECUTED_REQUIRES_RUNTIME` |
| REQ-008 | Public release with evidence | `UNEXECUTED_REQUIRES_RUNTIME` |

---

## 5. Audit 1 — Security Findings

**Severity scale:** critical → high → medium → low

### 5.1 Critical Security Additions

| ID | Category | Severity | Finding | Mitigation |
|----|----------|----------|---------|------------|
| SEC-CAP-001 | Capability authorization | **critical** | Model can request any tool if output parsed naively | Every tool call authorized **outside model** via policy engine |
| SEC-NET-001 | Network policy | **critical** | URL fetch enables SSRF and data exfiltration | Explicit capability; private IP block; redirect validation; allowlist option |
| SEC-PLG-001 | Plugin sandbox | **critical** | Same-process plugins inherit agent privileges | **Subprocess plugins** with restricted IPC and capability tokens |
| SEC-INJ-001 | Prompt injection | **critical** | Retrieved docs and user files can inject tool directives | Retrieved content **untrusted (T2)**; documents cannot grant authority |
| SEC-CHK-001 | Checkpoint safety | **critical** | Pickle deserialization enables arbitrary code execution | **No pickle**; SQLite + JSON + checksums + schema versioning |

### 5.2 Additional Security Requirements

| ID | Category | Severity | Mitigation |
|----|----------|----------|------------|
| SEC-WS-001 | Workspace escape | high | Canonical path resolution; symlink deny; protected path list |
| SEC-ED-001 | Stale edit overwrite | high | SHA-256 pre-check; rollback on mismatch |
| SEC-SEC-001 | Secret exfiltration | critical | Deny read of `.env`, credentials; audit all file reads |
| SEC-DOS-001 | Resource exhaustion | medium | Timeouts, output limits, memory caps on subprocesses |
| SEC-AUD-001 | Audit gap | medium | Immutable event log for all mutating operations |

### 5.3 Trust Boundary Position

The **policy engine** sits between trust levels T3 (model output), T4 (plugin code), and T5 (external network) and all privileged operations (filesystem write, subprocess spawn, network).

---

## 6. Audit 1 — Reliability Invariants

These ten invariants must hold in every release candidate build. Violation of any invariant is **release-blocking**.

| ID | Invariant |
|----|-----------|
| REL-001 | **No partial file edit may be committed** — atomic commit or full rollback |
| REL-002 | **No tool may escape capability scope** — policy engine is authoritative |
| REL-003 | **Every mutating action has an audit record** — append-only event log |
| REL-004 | **Every task has an idempotency identifier** — safe retry without duplicate effects |
| REL-005 | **Every external process has a timeout** — no hung subprocess |
| REL-006 | **Every subprocess has memory and output limits** — bounded resource use |
| REL-007 | **Every index update is transactional** — SQLite WAL + explicit transactions |
| REL-008 | **Failed task cannot silently mark success** — terminal states are explicit |
| REL-009 | **Model restart cannot corrupt persistent state** — inference isolated from state store |
| REL-010 | **Recovery resumes from deterministic checkpoint boundary** — no ambiguous resume |

### 6.1 Invariant Verification Method

| Invariant | Test slice | Harness |
|-----------|------------|---------|
| REL-001 | SLICE 8, 21 | Reliability harness (SLICE 23) |
| REL-002 | SLICE 7, 22 | Security harness |
| REL-003 | SLICE 3 | Audit log integration tests |
| REL-004 | SLICE 17 | Agent loop tests |
| REL-005 | SLICE 9, 18 | Timeout injection tests |
| REL-006 | SLICE 9, 18 | Resource limit tests |
| REL-007 | SLICE 10, 11 | SQLite corruption recovery |
| REL-008 | SLICE 17, 21 | State machine tests |
| REL-009 | SLICE 4, 20 | Model crash simulation |
| REL-010 | SLICE 20, 21 | Checkpoint recovery suite |

---

## 7. Audit 1 — Performance Findings

### 7.1 Rejected Approach

| Approach | Status | Reason |
|----------|--------|--------|
| Universal fixed thresholds (e.g., "inference < 2s", "index < 500ms") | **REJECTED** | Hardware variance makes fixed thresholds false pass/fail |

### 7.2 Required Approach: Device/Model Profiles

Performance acceptance uses **profiles** that define budgets relative to baseline measurements on reference hardware.

| Profile | Reference hardware | Metrics captured |
|---------|-------------------|------------------|
| `desktop_reference` | 16GB RAM, 8-core, no GPU requirement | Latency p50/p95, peak RAM, tokens/sec |
| `android_mid` | 6GB RAM ARM64 phone | Model load time, inference tokens/sec, index size |
| `ios_mid` | A15+ class iPhone | XCFramework load, thermal throttle events |
| `low_ram_mobile` | 4GB RAM | Degraded mode: smaller quant, FTS-only |

### 7.3 Performance Evidence Requirements

1. Each benchmark run records `profile`, `model_id`, `quant`, `context_length`, `device_id`.
2. Results stored as JSON in `evidence/performance/<profile>/`.
3. Regression detected when p95 latency exceeds **1.5× profile baseline** (not a universal constant).
4. Memory ceiling is **profile maximum** documented in MOBILE.md, not a single global number.

### 7.4 Performance Risks

| Risk | Impact | Mitigation slice |
|------|--------|------------------|
| Large model OOM on mobile | Agent unusable | SLICE 29 resource manager |
| Index rebuild blocks UI | Poor UX | SLICE 28 incremental indexing |
| Semantic search slower than FTS | User disables knowledge | SLICE 15 orchestrator with FTS fallback |
| Cold start model load | Timeout on first task | SLICE 27 preload strategy |

---

## 8. Audit 2 — Architecture and Threat Model

### 8.1 Architecture Diagram (ASCII)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER / IDE CLIENT                               │
│                         (trusted — issues tasks, approvals)                  │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │ user_request, approvals
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TASK CONTROLLER (T0)                               │
│              plan · cancel · retry · checkpoint schedule                     │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
┌───────────────┐         ┌─────────────────┐         ┌─────────────────┐
│ CONTEXT MGR   │         │ CHECKPOINT SYS  │         │  AUDIT / EVENT  │
│ token budget  │         │ (T0 persistent) │         │  LOG (T0)       │
│ compaction    │         │ no pickle       │         │  append-only    │
└───────┬───────┘         └─────────────────┘         └─────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        KNOWLEDGE SERVICE                                     │
│  ┌─────────────┐   ┌──────────────┐   ┌─────────────────────────────────┐ │
│  │ SQLite (T1) │   │ FTS5 (T1)    │   │ Chroma adapter (optional, T1)   │ │
│  │ authoritative│   │ lexical      │   │ semantic overlay — not authority│ │
│  └─────────────┘   └──────────────┘   └─────────────────────────────────┘ │
│  ┌─────────────┐                                                            │
│  │ Embedding   │  nomic-embed-text / configurable                             │
│  │ Provider    │                                                            │
│  └─────────────┘                                                            │
│  Retrieved chunks wrapped as UNTRUSTED (T2) before model context            │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │ untrusted context + task prompt
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MODEL GATEWAY                                        │
│   OllamaProvider │ LlamaCppProvider │ MockProvider                           │
│   Output: T3 — UNTRUSTED structured JSON                                   │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │ TOOL_CALL | EDIT_REQUEST | FINAL
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    OUTPUT VALIDATOR + POLICY ENGINE (T0)                     │
│         ═══════════════ TRUST BOUNDARY ═══════════════                       │
│   parse schema · default deny · capability scope · approval queue          │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │ PolicyDecision.allowed == true
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          TOOL GATEWAY (T0)                                   │
│  ┌──────────────┐  ┌──────────────────┐  ┌────────────────────────────┐  │
│  │ Workspace    │  │ Transactional    │  │ Test Runner                │  │
│  │ Guard (T1)   │  │ Edit Engine      │  │ (allowlist, timeout)       │  │
│  └──────────────┘  └──────────────────┘  └────────────────────────────┘  │
│  ┌──────────────┐  ┌──────────────────┐                                    │
│  │ Plugin       │  │ Network tools    │  disabled by default (T5)          │
│  │ Supervisor   │  │ (if enabled)     │                                    │
│  │ subprocess   │  │ SSRF controls    │                                    │
│  │ T4 isolated  │  │                  │                                    │
│  └──────────────┘  └──────────────────┘                                    │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │ tool results
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AGENT LOOP OBSERVE → next state                      │
└─────────────────────────────────────────────────────────────────────────────┘

Data flow legend:
  T0 → trusted system components
  T1 → user project files and local indexes
  T2 → retrieved knowledge (untrusted content)
  T3 → model output (untrusted structured data)
  T4 → plugin subprocess code
  T5 → external network
```

### 8.2 Threat Model — Trust Levels T0–T5

| Level | Name | Description | Default handling |
|-------|------|-------------|------------------|
| **T0** | Trusted system | Agent core, policy engine, audit log, checkpoint store | Full privilege within defined capability table |
| **T1** | User project | Files in workspace, SQLite indexes derived from workspace | Read allowed; write via transactional edit only |
| **T2** | Retrieved knowledge | Chunks from ingestion/retrieval | **Untrusted content** — wrapped, cannot grant capabilities |
| **T3** | Model output | LLM JSON/text responses | **Untrusted** — parsed, never directly executed |
| **T4** | Plugin code | Subprocess plugin binaries/scripts | Isolated process; capability token limits scope |
| **T5** | External network | Remote URLs, APIs | **Disabled by default**; SSRF controls when enabled |

### 8.3 Threat Actors

| Actor | Capability | Primary controls |
|-------|------------|------------------|
| Malicious project file | Inject prompts via source/comments | T2 wrapper; policy engine |
| Malicious retrieved doc | Tool directive injection | SEC-INJ-001; no authority from T2 |
| Compromised model output | Request denied tools | Policy engine default deny |
| Malicious plugin | Escape sandbox | Subprocess + token; no same-process |
| Network attacker | SSRF, exfiltration | SEC-NET-001; disabled by default |
| Local attacker | Read secrets outside workspace | Workspace guard; protected paths |

### 8.4 Default Security Policy String

```
READ=workspace; WRITE=transactional; DELETE=approval; SHELL=sandbox+capability;
NETWORK=disabled; PLUGIN=subprocess+token; SECRETS=deny
```

---

## 9. Audit 2 — Tool Risk Classes and Default Policy

### 9.1 Risk Class Definitions

| Class | Enum | Description | Default policy |
|-------|------|-------------|----------------|
| **READ_ONLY** | `READ_ONLY` | No mutation of filesystem, process, or network state | Auto-approve within workspace scope |
| **MUTATING_APPROVAL** | `MUTATING_APPROVAL` | Changes state; reversible or bounded | Auto-approve if policy allows; user approval for protected paths |
| **HIGH_RISK** | `HIGH_RISK` | Subprocess, network, delete, plugin spawn | Requires explicit capability + often user approval |

### 9.2 Tool Classification Table

| Tool | Risk class | Default allowed | Notes |
|------|------------|-----------------|-------|
| `list_files` | READ_ONLY | yes | Workspace only |
| `read_file` | READ_ONLY | yes | Protected paths denied |
| `search_files` | READ_ONLY | yes | FTS5 / grep scoped |
| `write_file` | MUTATING_APPROVAL | conditional | New files yes; overwrite needs hash check |
| `edit_file` | MUTATING_APPROVAL | conditional | Transactional edit engine |
| `run_tests` | HIGH_RISK | conditional | Allowlist + timeout |
| `git_status` | READ_ONLY | yes | No git write in v1 |
| `shell_exec` | HIGH_RISK | **no** | Not in SLICE 6; future with strict sandbox |
| `fetch_url` | HIGH_RISK | **no** | Network disabled by default |
| `spawn_plugin` | HIGH_RISK | conditional | Capability token required |

### 9.3 Policy Decision Structure

```json
{
  "allowed": false,
  "reason": "default deny",
  "required_approval": true,
  "capability_scope": ["read:workspace", "write:workspace"]
}
```

---

## 10. Audit 2 — Knowledge Security

### 10.1 Principles

1. **SQLite is authoritative** — all document/chunk truth lives in SQLite tables.
2. **Chroma is optional** — semantic search is a cache/overlay; removable without data loss.
3. **FTS5 always available** — lexical search requires no embedding provider.
4. **Retrieved content is untrusted (T2)** — wrapped before inclusion in model context.
5. **Knowledge cannot grant authority** — no tool capability embedded in indexed text can affect policy.

### 10.2 Ingestion Security

| Control | Implementation |
|---------|----------------|
| Path scope | Only ingest from workspace via Workspace Guard |
| Parser isolation | Parser failures do not crash indexer |
| Hash deduplication | `source_hash` prevents stale re-embed |
| Version tracking | `parser_version`, `chunker_version` on each document |
| Embedding provenance | `embedding_model`, dimension stored per document |

### 10.3 Retrieval Security

| Control | Implementation |
|---------|----------------|
| Untrusted wrapper | Prefix retrieved chunks with trust marker |
| Token budget | Hard limit before model call |
| Citation metadata | Path + chunk id for audit, not for policy |
| Injection test | SEC harness includes malicious doc retrieval |

### 10.4 Chroma-Specific Controls

| Risk | Mitigation |
|------|------------|
| Chroma becomes sole store | Rejected — SQLite authoritative |
| Chroma version drift | Collection versioning tied to embedding model |
| Chroma unavailable | Automatic FTS5 fallback in orchestrator |
| Poisoned embeddings | Rebuild command; hash-linked to source chunks |

---

## 11. Audit 3 — Implementation Feasibility Gaps and Corrections

### 11.1 Feasibility Assessment Summary

| Area | Feasible? | Conditions |
|------|-----------|------------|
| Model abstraction | Yes | Mock provider for CI; Ollama + llama.cpp adapters |
| Policy outside model | Yes | Default-deny table; no prompt-only security |
| SQLite + FTS5 knowledge | Yes | Standard SQLite FTS5 extension |
| Optional Chroma | Yes | Adapter pattern; FTS5 fallback tested |
| Transactional edits | Yes | Temp file + syntax check + atomic rename |
| Subprocess plugins | Yes | JSON-RPC over stdin/stdout; capability tokens |
| Safe checkpoints | Yes | JSON schema + SHA-256; explicit ban on pickle |
| Mobile llama.cpp | Yes | ARM64 Android; iOS XCFramework documented |
| Mobile Python | Partial | Android Termux only; **not iOS** |
| Full adversarial suite | Yes | Dedicated SLICE 22 harness |
| v1.0.0 in single effort | No | 37 slices; phased release required |

### 11.2 Implementation Gaps Identified

| Gap ID | Description | Correction | Target slice |
|--------|-------------|------------|--------------|
| IMP-001 | No model gateway exists | Implement provider interface | SLICE 4 |
| IMP-002 | No policy engine | Implement before any write tool | SLICE 7 |
| IMP-003 | Chroma assumed primary | SQLite first; Chroma adapter optional | SLICE 10–13 |
| IMP-004 | Plugin in-process design | Subprocess supervisor | SLICE 18 |
| IMP-005 | Pickle checkpoint reference in source roadmap | Ban pickle; schema versioning | SLICE 20 |
| IMP-006 | Fixed Qwen model | Model matrix + benchmarks | SLICE 25 |
| IMP-007 | No audit event log | Append-only events | SLICE 3 |
| IMP-008 | Direct write_file | Transactional edit protocol | SLICE 8 |
| IMP-009 | iOS Python assumption | Swift + llama.cpp | SLICE 27 |
| IMP-010 | No evidence package | Evidence record format + CI artifacts | SLICE 23+ |

### 11.3 Technology Stack (Corrected)

| Layer | Technology | Role |
|-------|------------|------|
| Language | Python 3.11+ (desktop/agent core) | Orchestration, tools, policy |
| Mobile iOS | Swift + llama.cpp XCFramework | On-device inference |
| Mobile Android | Kotlin/Java or Termux path + native inference | On-device inference |
| State store | SQLite 3 + FTS5 | Authoritative knowledge and events |
| Semantic (optional) | ChromaDB | Vector overlay |
| Embeddings | nomic-embed-text via Ollama | Configurable provider |
| Inference desktop | Ollama | Local HTTP API |
| Inference portable | llama.cpp + GGUF | Mobile and offline |
| Test | pytest | Unit, integration, security |
| Packaging | pyproject.toml + lockfile | Reproducible installs |

---

## 12. Audit 3 — SQLite Data Model

### 12.1 Schema Overview

```
projects ──< files
projects ──< documents ──< chunks ──< chunks_fts (FTS5 virtual)
projects ──< tasks ──< events
tasks ──< checkpoints
```

### 12.2 Table Definitions

#### `projects`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | TEXT | PRIMARY KEY | UUID |
| `root_path` | TEXT | NOT NULL UNIQUE | Canonical workspace root |
| `name` | TEXT | NOT NULL | Display name |
| `created_at` | TEXT | NOT NULL | ISO-8601 timestamp |
| `updated_at` | TEXT | NOT NULL | ISO-8601 timestamp |

#### `files`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | TEXT | PRIMARY KEY | UUID |
| `project_id` | TEXT | NOT NULL FK → projects | Parent project |
| `relative_path` | TEXT | NOT NULL | Path relative to root |
| `sha256` | TEXT | NOT NULL | Content hash at last index |
| `indexed_at` | TEXT | NOT NULL | Last successful index time |

#### `documents`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | TEXT | PRIMARY KEY | UUID |
| `project_id` | TEXT | NOT NULL FK → projects | Parent project |
| `file_id` | TEXT | FK → files | Source file if applicable |
| `source_hash` | TEXT | NOT NULL | Hash of raw source bytes |
| `embedding_model` | TEXT | | Model id used for embeddings |
| `parser_version` | TEXT | NOT NULL | Parser semver |
| `chunker_version` | TEXT | NOT NULL | Chunker semver |
| `created_at` | TEXT | NOT NULL | ISO-8601 |

#### `chunks`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | TEXT | PRIMARY KEY | UUID |
| `document_id` | TEXT | NOT NULL FK → documents | Parent document |
| `ordinal` | INTEGER | NOT NULL | Order within document |
| `text` | TEXT | NOT NULL | Chunk text content |
| `hash` | TEXT | NOT NULL | Hash of chunk text |
| `token_count` | INTEGER | | Estimated tokens |

#### `chunks_fts` (FTS5 virtual table)

| Column | Type | Description |
|--------|------|-------------|
| `chunk_id` | UNINDEXED | Reference to chunks.id |
| `text` | indexed | FTS5 indexed text |

#### `tasks`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | TEXT | PRIMARY KEY | UUID |
| `project_id` | TEXT | NOT NULL FK → projects | Parent project |
| `user_request` | TEXT | NOT NULL | Original user prompt |
| `status` | TEXT | NOT NULL | Agent task status enum |
| `idempotency_key` | TEXT | UNIQUE | Retry safety |
| `created_at` | TEXT | NOT NULL | ISO-8601 |
| `updated_at` | TEXT | NOT NULL | ISO-8601 |

#### `events`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | TEXT | PRIMARY KEY | UUID |
| `task_id` | TEXT | NOT NULL FK → tasks | Parent task |
| `event_type` | TEXT | NOT NULL | e.g. TOOL_REQUEST |
| `payload_json` | TEXT | NOT NULL | Event details |
| `created_at` | TEXT | NOT NULL | ISO-8601 append-only |

#### `checkpoints`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | TEXT | PRIMARY KEY | UUID |
| `task_id` | TEXT | NOT NULL FK → tasks | Parent task |
| `sequence` | INTEGER | NOT NULL | Monotonic per task |
| `schema_version` | TEXT | NOT NULL | Checkpoint schema semver |
| `state_json` | TEXT | NOT NULL | Serialized state |
| `state_hash` | TEXT | NOT NULL | SHA-256 of state_json |
| `created_at` | TEXT | NOT NULL | ISO-8601 |

### 12.3 Indexes

```sql
CREATE INDEX idx_files_project ON files(project_id);
CREATE INDEX idx_documents_project ON documents(project_id);
CREATE INDEX idx_documents_source_hash ON documents(source_hash);
CREATE INDEX idx_chunks_document ON chunks(document_id);
CREATE INDEX idx_tasks_project ON tasks(project_id);
CREATE INDEX idx_events_task ON events(task_id);
CREATE INDEX idx_checkpoints_task ON checkpoints(task_id, sequence);
```

---

## 13. Audit 3 — Agent State Machine

### 13.1 States

| State | Description |
|-------|-------------|
| `CREATED` | Task record created; not yet planning |
| `PLANNING` | Agent decomposing user request |
| `RETRIEVING` | Knowledge service fetching context |
| `READY_TO_ACT` | Context assembled; awaiting model call |
| `TOOL_REQUEST` | Model returned tool call; pending validation |
| `POLICY_CHECK` | Policy engine evaluating tool request |
| `EXECUTING` | Tool gateway running approved tool |
| `OBSERVING` | Processing tool result; updating context |
| `VALIDATING` | Verifying task completion criteria |
| `COMPLETED` | Terminal success |
| `FAILED` | Terminal failure with reason |
| `CANCELLED` | User or system cancelled |
| `BLOCKED` | Waiting for user approval or input |
| `RECOVERY_REQUIRED` | Checkpoint restore needed |

### 13.2 State Transition Diagram (ASCII)

```
                    ┌──────────┐
                    │ CREATED  │
                    └────┬─────┘
                         │
                         ▼
                    ┌──────────┐
         ┌──────────│ PLANNING │──────────┐
         │          └────┬─────┘          │
         │               │              │
         │               ▼              │
         │          ┌──────────┐        │
         │          │RETRIEVING│        │
         │          └────┬─────┘        │
         │               │              │
         │               ▼              │
         │       ┌───────────────┐      │
         │       │ READY_TO_ACT  │      │
         │       └───────┬───────┘      │
         │               │              │
         │     ┌─────────┼─────────┐    │
         │     ▼         ▼         ▼    │
         │  FINAL   TOOL_CALL  EDIT_REQ  │
         │     │         │         │    │
         │     │         ▼         │    │
         │     │    ┌────────────┐ │    │
         │     │    │TOOL_REQUEST│ │    │
         │     │    └─────┬──────┘ │    │
         │     │          ▼        │    │
         │     │    ┌────────────┐ │    │
         │     │    │POLICY_CHECK│ │    │
         │     │    └─────┬──────┘ │    │
         │     │     deny │ allow  │    │
         │     │          ▼        │    │
         │     │    ┌──────────┐  │    │
         │     │    │EXECUTING │  │    │
         │     │    └────┬─────┘  │    │
         │     │         ▼        │    │
         │     │    ┌──────────┐  │    │
         │     │    │OBSERVING │──┘    │
         │     │    └────┬─────┘       │
         │     │         │ loop        │
         │     ▼         ▼             │
         │  ┌──────────┐               │
         │  │VALIDATING│               │
         │  └────┬─────┘               │
         │   pass│ fail                │
         │       ▼                     ▼
         │  ┌──────────┐        ┌──────────┐
         │  │COMPLETED │        │  FAILED  │
         │  └──────────┘        └──────────┘

  CANCELLED ← (any non-terminal state, user cancel)
  BLOCKED ← (approval required)
  RECOVERY_REQUIRED ← (crash restore from checkpoint)
```

### 13.3 Model Response Types

| Type | Triggers transition |
|------|---------------------|
| `FINAL` | → VALIDATING |
| `TOOL_CALL` | → TOOL_REQUEST |
| `EDIT_REQUEST` | → TOOL_REQUEST (edit_file path) |
| `CLARIFICATION` | → BLOCKED |
| `ERROR_RECOVERY` | → PLANNING or RECOVERY_REQUIRED |

---

## 14. Audit 3 — Edit Protocol

### 14.1 Edit Request Structure

```json
{
  "path": "src/example.py",
  "expected_sha256": "abc123...",
  "operations": [
    {
      "kind": "SEARCH_REPLACE",
      "search": "old_code",
      "replace": "new_code",
      "offset": 0
    }
  ]
}
```

### 14.2 Operation Kinds

| Kind | Fields | Description |
|------|--------|-------------|
| `SEARCH_REPLACE` | search, replace, offset | Replace first match from offset |
| `INSERT` | offset, replace (inserted text) | Insert at byte offset |
| `DELETE` | search, offset | Delete matched region |

### 14.3 Edit Pipeline (Mandatory Order)

```
1. resolve_workspace_path(path)
2. is_allowed_path(path) → deny if false
3. read current file; compute sha256
4. compare sha256 to expected_sha256 → STALE_CONTEXT error if mismatch
5. copy to temp file in workspace .agent/tmp/
6. apply operations sequentially on temp copy
7. run syntax_check(temp_path, language)
8. if syntax_check fails → delete temp, return SYNTAX_ERROR
9. atomic rename temp → target path
10. emit FILE_EDITED event with before_hash, after_hash
11. update files table sha256 in SQLite (transactional)
```

### 14.4 Error Codes

| Code | Meaning | Agent action |
|------|---------|--------------|
| `STALE_CONTEXT` | File changed since read | Re-read and re-plan |
| `SYNTAX_ERROR` | Post-edit parse/compile failed | Rollback; retry edit |
| `PATH_DENIED` | Outside workspace or protected | Fail tool; audit log |
| `OPERATION_FAILED` | Search string not found | Retry with updated context |
| `ATOMIC_COMMIT_FAILED` | FS error on rename | Rollback; RECOVERY_REQUIRED |

### 14.5 Reliability Invariants Applied

- REL-001: No partial commit — step 9 is atomic rename only after step 7 passes.
- REL-003: Step 10 always emits audit event on success.

---

## 15. Audit 3 — Final Findings

### 15.1 Audit 3 Verdict

**Implementation is feasible** with the corrections documented in this blueprint. The original 13-phase roadmap is **not implementable as written**.

### 15.2 Blocking Issues (Must resolve before Phase 0 code)

| ID | Issue | Resolution |
|----|-------|------------|
| BLK-001 | Fixed Qwen3-Coder-7B dependency | Model matrix (Section 4.2) |
| BLK-002 | Chroma as authority | SQLite + FTS5 (Section 10) |
| BLK-003 | Same-process plugins | Subprocess design (SLICE 18) |
| BLK-004 | Pickle checkpoints | Safe checkpoint schema (SLICE 20) |
| BLK-005 | No policy engine | SLICE 7 before write tools |

### 15.3 Non-Blocking Recommendations

| ID | Recommendation | Slice |
|----|----------------|-------|
| REC-001 | Mock provider for all CI agent tests | SLICE 4 |
| REC-002 | Evidence record on every slice completion | All |
| REC-003 | nightly reliability harness | SLICE 23 |
| REC-004 | Document threat model alongside code | SLICE 32 |
| REC-005 | SBOM at RC freeze | SLICE 33 |

### 15.4 Audit Completion Record

| Audit | Status | Date |
|-------|--------|------|
| Audit 1 — Requirements and Evidence | Complete | 2026-08-08 |
| Audit 2 — Architecture and Threat Model | Complete | 2026-08-08 |
| Audit 3 — Implementation Feasibility | Complete | 2026-08-08 |

---

## 16. Slice-by-Slice Blueprint (SLICE 0 – SLICE 36)

**Rule:** A slice is complete only when acceptance criteria have **executable evidence** — not when code exists.

**Default gate status for all slices:** `UNEXECUTED_REQUIRES_RUNTIME`

## 16. Slice-by-Slice Blueprint (SLICE 0 – SLICE 36)


### SLICE 0 — Repository and Engineering Contract

| Field | Value |
|-------|-------|
| **Depends on** | None |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Create repository skeleton and engineering rules

**Deliverables:**

- `src/` package layout with clear module boundaries
- `tests/` with pytest runner and fixtures
- `fixtures/` for deterministic agent-loop tests
- `plugins/` directory with example manifest
- `docs/` with architecture and security stubs
- `pyproject.toml` with locked dev dependencies
- `README.md` with honest capability statement
- `SECURITY.md` with vulnerability reporting process

**Acceptance:**

- Clean checkout installs without network for basic unit tests
- Test runner executes in CI and locally with identical results
- No network required for foundation slice tests
- Engineering contract documented in CONTRIBUTING.md


### SLICE 1 — Configuration

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 0 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Create validated configuration system

**Deliverables:**

- `workspace_root` path validation
- `model_provider` selection (ollama | llama_cpp | mock)
- `embedding_provider` selection
- `network_enabled` boolean with default false
- Schema-validated config file (JSON or TOML)
- Secret resolution from environment only

**Acceptance:**

- Invalid configuration rejected at startup with actionable error
- Secrets never stored in source or config files
- Configuration changes require restart; no hot-reload of security flags


### SLICE 2 — Workspace Guard

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 1 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Filesystem security boundary for all file operations

**Deliverables:**

- `resolve_workspace_path()` — canonical path resolution
- `is_allowed_path()` — workspace containment check
- `is_protected_path()` — deny list (.env, credentials)
- `read_file()` / `write_file()` / `delete_file()` gated APIs

**Acceptance:**

- Path traversal (`../`, encoded variants) rejected
- Symlink escape outside workspace rejected
- Protected paths (.env, .git/config) cannot be read or written by agent
- All denied paths logged to audit event stream


### SLICE 3 — Event and Audit Log

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 2 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Record every meaningful agent action immutably

**Deliverables:**

- Event types: `TASK_CREATED`, `TOOL_REQUEST`, `POLICY_DENIED`, `FILE_EDITED`, `CHECKPOINT_CREATED`
- Append-only event store (SQLite or JSONL)
- Correlation IDs linking task → tool → outcome
- Export command for evidence package

**Acceptance:**

- Every tool execution produces exactly one immutable event record
- Events include timestamp, actor, input hash, outcome
- Audit log survives process crash without corruption


### SLICE 4 — Model Gateway

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 3 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Abstract model execution behind provider interface

**Deliverables:**

- `OllamaProvider` — HTTP local inference
- `LlamaCppProvider` — direct GGUF inference
- `MockProvider` — deterministic fixture responses
- `generate()`, `stream()`, `health()`, `capabilities()`

**Acceptance:**

- Mock provider passes all agent-loop unit tests without real model
- Provider swap requires only config change
- Health check detects unavailable model before task start


### SLICE 5 — Structured Model Output

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 4 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Machine-verifiable model response parsing

**Deliverables:**

- Response types: `FINAL`, `TOOL_CALL`, `EDIT_REQUEST`, `CLARIFICATION`, `ERROR_RECOVERY`
- JSON schema validation per response type
- Parser rejects malformed output with recovery path

**Acceptance:**

- Invalid output never directly executes tools or edits
- Parser fuzz tests cover truncated/malformed JSON
- Clarification path pauses agent until user responds


### SLICE 6 — Tool Registry

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 5 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Tools independent of model implementation

**Deliverables:**

- `list_files`, `read_file`, `search_files`
- `write_file`, `edit_file`
- `run_tests`, `git_status`
- Tool metadata: name, risk class, input schema

**Acceptance:**

- No arbitrary shell tool in this slice
- Each tool registered with explicit risk class
- Tool list exposed to policy engine before execution


### SLICE 7 — Policy Engine

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 6 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Deterministic tool authorization outside model

**Deliverables:**

- `PolicyDecision` struct: allowed, reason, required_approval, capability_scope
- Default-deny policy table
- User approval queue for MUTATING_APPROVAL tools

**Acceptance:**

- Model cannot bypass policy via JSON injection or natural language
- Denied requests produce `POLICY_DENIED` audit event
- Policy rules loaded from config, not model prompt


### SLICE 8 — Transactional Edit Engine

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 7 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Safe source edits with atomic commit

**Deliverables:**

- Pre-edit SHA-256 hash verification
- Temp copy + apply operations + syntax check
- Atomic rename commit or full rollback
- Edit operation kinds: SEARCH_REPLACE, INSERT, DELETE

**Acceptance:**

- Stale-context overwrites prevented when file changed since read
- Syntax check failure rolls back without partial write
- Every committed edit produces `FILE_EDITED` event with before/after hash


### SLICE 9 — Test Runner

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 8 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Execute project tests safely

**Deliverables:**

- Command allowlist per project type
- Timeout enforcement per test invocation
- Stdout/stderr size limits
- Process-tree cleanup on timeout or cancel

**Acceptance:**

- Exit code captured and returned to agent
- Sandboxing strategy documented in SECURITY.md
- Runaway test process killed within timeout + grace period


### SLICE 10 — Knowledge SQLite Store

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 9 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Authoritative document and chunk storage

**Deliverables:**

- Tables: `projects`, `files`, `documents`, `chunks`
- Foreign keys and indexes
- Deduplication by source_hash
- Versioned parser metadata columns

**Acceptance:**

- Duplicate ingestion skipped when source_hash matches
- Schema migrations versioned and tested
- Store is sole authoritative source for indexed content


### SLICE 11 — FTS5 Search

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 10 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Deterministic lexical search fallback

**Deliverables:**

- FTS5 virtual table on chunk text
- Exact phrase, symbol, case-insensitive queries
- Ranking by BM25 or equivalent
- SQL injection hardening via parameterized queries

**Acceptance:**

- FTS5 operates without Chroma or embedding provider
- Corruption recovery test rebuilds index from chunks
- Search latency profile recorded per device class


### SLICE 12 — Embedding Provider

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 11 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Embedding abstraction layer

**Deliverables:**

- `embed(text) -> vector`
- `model_id`, `dimension`, `health()`
- `OllamaEmbeddingProvider` initial adapter

**Acceptance:**

- Embedding model_id and dimension persisted with each document
- Provider failure degrades to FTS5-only retrieval
- Batch embedding respects memory limits


### SLICE 13 — Chroma Adapter

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 12 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Optional semantic search layer

**Deliverables:**

- Collection versioning aligned with embedding model
- `rebuild` command for index refresh
- Automatic fallback to FTS5 when Chroma unavailable

**Acceptance:**

- Chroma is never authoritative; SQLite remains source of truth
- Removing Chroma package does not break agent
- Semantic search results tagged as untrusted in context


### SLICE 14 — Knowledge Ingestion

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 13 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Source ingestion adapters

**Deliverables:**

- Parsers: Python, JavaScript, Markdown, TXT, PDF, HTML
- Chunker with configurable size and overlap
- Persist: source_hash, parser_version, chunker_version, embedding_model

**Acceptance:**

- Re-ingest updates chunks when source_hash changes
- Parser failure isolated per file; batch continues
- Ingestion produces evidence record per format


### SLICE 15 — Retrieval Orchestrator

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 14 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Lexical + semantic retrieval with trust wrapper

**Deliverables:**

- FTS5 candidate retrieval
- Semantic candidate retrieval (when available)
- Deduplicate and rerank merged results
- Untrusted wrapper on all retrieved content

**Acceptance:**

- Token budget enforced before context assembly
- Retrieved content cannot contain capability directives that bypass policy
- Citation metadata preserved for audit


### SLICE 16 — Agent Context Manager

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 15 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Control context growth and compaction

**Deliverables:**

- Token budgeting per task phase
- Compaction strategy for long conversations
- Retrieved-context size limits
- Checkpoint boundary markers for long tasks

**Acceptance:**

- Context never exceeds configured token ceiling
- Compaction preserves task-critical state
- Long tasks checkpoint before compaction


### SLICE 17 — Core Agent Loop

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 16 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Recoverable coding agent orchestration

**Deliverables:**

- States: plan → retrieve → model → validate → policy → tool → observe → complete
- Cancellation and timeout handling
- Mock-model integration tests

**Acceptance:**

- Mock-model tests pass before any real-model testing
- Agent completes deterministic fixture tasks end-to-end
- Failed step does not advance state machine incorrectly


### SLICE 18 — Plugin Supervisor

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 17 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Subprocess plugin architecture

**Deliverables:**

- Plugin manifest schema (name, version, permissions)
- Capability token issuance per spawn
- Restricted IPC channel (stdin/stdout JSON-RPC or equivalent)

**Acceptance:**

- Plugin receives only explicitly granted capabilities
- Plugin crash does not crash agent core
- Spawn failure logged and task continues or fails gracefully


### SLICE 19 — Plugin Lifecycle

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 18 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Discovery, validation, startup, health, reload, shutdown

**Deliverables:**

- Plugin discovery from configured directories
- Duplicate tool name rejection
- Health polling and failure isolation
- Graceful shutdown with timeout

**Acceptance:**

- Malicious plugin cannot escape subprocess boundary
- Plugin with invalid manifest rejected at load
- Reload does not leak capability tokens


### SLICE 20 — Checkpoint System

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 17 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Safe recovery without pickle deserialization

**Deliverables:**

- Checkpoint payload: task state, conversation state, schema_version, state_hash
- SQLite or JSON storage with checksum
- Create and restore APIs

**Acceptance:**

- No arbitrary pickle deserialization anywhere in codebase
- Corrupted checkpoint detected by hash mismatch
- Schema version mismatch triggers migration or safe failure


### SLICE 21 — Recovery Engine

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 20 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Failure scenario testing and deterministic resume

**Deliverables:**

- Scenarios: model crash, tool timeout, corrupted checkpoint, interrupted edit
- Recovery boundary selection logic
- User notification on `RECOVERY_REQUIRED`

**Acceptance:**

- Deterministic recovery from last valid checkpoint
- Interrupted edit rolled back completely
- Recovery tests produce evidence records


### SLICE 22 — Security Test Harness

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 21 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Adversarial regression suite

**Deliverables:**

- Tests: prompt injection, path traversal, SSRF, malicious plugin, recursive tools
- Automated CI integration
- Severity classification per finding

**Acceptance:**

- Zero critical/high release-blocking findings at slice exit
- Each test produces evidence record with artifacts
- Regression suite runs on every PR


### SLICE 23 — Reliability Harness

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 22 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Automated failure scenario suite

**Deliverables:**

- Fields: test_id, timestamp, expected, actual, PASS/FAIL, artifacts
- Crash injection hooks
- Chaos tests for subprocess and model providers

**Acceptance:**

- Every test produces evidence record
- Harness runs in CI nightly
- Failure artifacts retained for 90 days minimum


### SLICE 24 — Knowledge Augmentation Benchmark

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 23 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Baseline vs augmented evaluation

**Deliverables:**

- Metrics: correctness, API hallucination rate, citation accuracy
- Fixture set with ground truth
- Comparison: no-retrieval vs FTS5 vs semantic

**Acceptance:**

- Results not based on self-reported faithfulness score only
- Benchmark JSON stored in evidence package
- Statistical summary with confidence intervals where applicable


### SLICE 25 — Model Benchmark

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 24 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Per-model fixture evaluation

**Deliverables:**

- Metrics: tool-call validity, JSON validity, edit accuracy, latency, memory
- Same fixture set for all models in compatibility matrix
- Device profile tagging

**Acceptance:**

- Each model profile produces comparable JSON report
- Out-of-memory handled gracefully with profile downgrade suggestion
- Latency recorded per operation class


### SLICE 26 — End-to-End Coding Tasks

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 25 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Ten real coding tasks with evidence acceptance

**Deliverables:**

- Tasks: auth fix, REST endpoint, refactor, tests, documentation, type fixes (10 total)
- Human-or-script verifier per task
- No model-as-judge-only acceptance

**Acceptance:**

- Each task has PASS/FAIL evidence record
- At least 7/10 tasks pass on reference desktop profile
- Failed tasks documented with root cause


### SLICE 27 — Mobile Core

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 26 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Android Termux + iOS Swift llama.cpp integration

**Deliverables:**

- Android: native inference path (Termux or embedded)
- iOS: XCFramework llama.cpp binding
- Shared mobile config schema

**Acceptance:**

- No iOS Python dependency for core product path
- Inference smoke test on reference devices
- Model load failure surfaces user-actionable error


### SLICE 28 — Mobile Knowledge Store

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 27 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** SQLite FTS5 on mobile with optional vectors

**Deliverables:**

- Incremental indexing on file change
- Storage quotas per device profile
- Battery-aware background indexing

**Acceptance:**

- Offline operation verified on physical device
- Index rebuild completes within quota time budget
- FTS5 works without network on mobile


### SLICE 29 — Mobile Resource Manager

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 28 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** RAM, storage, thermal, battery adaptation

**Deliverables:**

- Model quantization selection by profile
- Context length adaptation
- Retrieval parallelism limits
- Thermal throttle detection

**Acceptance:**

- Device capability profiles documented and tested
- No universal fixed thresholds; per-profile budgets
- Degradation path: semantic → FTS5 → reduced context


### SLICE 30 — Mobile Security

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 29 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Platform isolation and integrity

**Deliverables:**

- No unauthorized network by default
- App storage isolation
- Model file integrity verification
- Plugin restrictions on mobile

**Acceptance:**

- Network tools disabled unless user enables capability
- Model tampering detected via checksum
- Plugins cannot access paths outside app sandbox


### SLICE 31 — Benchmark Harness

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 30 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Reproducible benchmark command

**Deliverables:**

- CLI: `agent benchmark --profile desktop|android|ios`
- Machine-readable JSON output
- Human-readable summary report

**Acceptance:**

- Benchmark completes on clean environment from lockfile
- JSON schema validated
- Results reproducible within documented variance


### SLICE 32 — Documentation

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 31 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Release documentation package

**Deliverables:**

- README, ARCHITECTURE, SECURITY, PLUGIN_API, MOBILE, BENCHMARKS, THREAT_MODEL
- Version alignment with implemented behavior
- Changelog for v1.0.0

**Acceptance:**

- Documentation review checklist signed
- No documented feature without test evidence
- Threat model matches implemented controls


### SLICE 33 — Release Candidate

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 32 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Freeze versions and generate SBOM

**Deliverables:**

- Dependency version lockfile
- Model versions and checksums
- Prompt and schema version tags
- Tool contract snapshots

**Acceptance:**

- Software Bill of Materials generated and stored
- All versions frozen in RC tag
- Upgrade path documented for post-1.0 patches


### SLICE 34 — Release Security Gate

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 33 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Zero critical/high findings verification

**Deliverables:**

- Workspace escape tests = 0 failures
- Unauthorized tool execution = 0
- Secret leakage = 0
- Unsafe deserialization = 0

**Acceptance:**

- Security harness re-run on RC build
- Third-party advisory scan completed
- Penetration test checklist for agent-specific threats


### SLICE 35 — Release Candidate Validation

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 34 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Full suite from clean environment

**Deliverables:**

- Logs, hashes, benchmark JSON, test reports, lockfile
- Independent reproduction script
- Evidence package assembly

**Acceptance:**

- Evidence independently reproducible by third party
- All slice acceptance criteria re-verified on RC
- No drift between RC and evidence timestamps


### SLICE 36 — v1.0.0

| Field | Value |
|-------|-------|
| **Depends on** | SLICE 35 |
| **Gate status** | `UNEXECUTED_REQUIRES_RUNTIME` |

**Goal:** Public release

**Deliverables:**

- Git tag `v1.0.0`
- Source release archive
- Documentation bundle
- Checksums and signatures
- SECURITY policy published

**Acceptance:**

- All gates pass with evidence package
- Public release gate six checks documented
- Post-release monitoring plan active


---

## 17. Three-Pass Implementability Review

Three independent implementability reviews were conducted after audit completion. **All three pass with conditions.**

### 17.1 Pass 1 — Structural Review

| Field | Value |
|-------|-------|
| **Result** | **PASS** |
| **Scope** | Slice dependencies, interfaces, module boundaries |

**Conditions (must hold during implementation):**

1. Each slice is buildable independently with explicit `depends_on` chain.
2. Dependencies are explicit — no hidden cross-slice coupling.
3. Interfaces (ModelGateway, PolicyEngine, ToolGateway, KnowledgeService) defined before consumers.
4. Persistent state schema defined before agent loop (SQLite tables Section 12).
5. Security boundaries explicit in architecture diagram (Section 8).

### 17.2 Pass 2 — Operational Review

| Field | Value |
|-------|-------|
| **Result** | **PASS** |
| **Scope** | Runability, degradation, recovery |

**Conditions:**

1. Agent runs without internet via `MockProvider` for CI and local dev.
2. Chroma removable — FTS5-only mode fully functional.
3. Model replaceable via configuration without code changes.
4. Plugins fail independently — core agent survives plugin crash.
5. Recovery after interruption via checkpoint boundary (SLICE 20–21).

### 17.3 Pass 3 — Security/Release Review

| Field | Value |
|-------|-------|
| **Result** | **PASS** |
| **Scope** | Threat model alignment, release safety |

**Conditions:**

1. Model output cannot directly execute privileged actions — policy gate mandatory.
2. Retrieved documents cannot grant authority — T2 untrusted wrapper.
3. SSRF controls on all network tools when network capability enabled.
4. Checkpoints cannot execute code — no pickle; schema-validated JSON only.
5. Stale edits cannot overwrite user changes — hash check in edit protocol.

### 17.4 Review Summary

| Pass | Name | Result | Blocking conditions |
|------|------|--------|---------------------|
| 1 | Structural | PASS | 5 conditions |
| 2 | Operational | PASS | 5 conditions |
| 3 | Security/Release | PASS | 5 conditions |

**Go decision allowed:** No — conditions require runtime implementation evidence.

---

## 18. Final Acceptance Matrix

| Area | Requirement | Status |
|------|-------------|--------|
| Model | Fixed Qwen3-Coder-7B | **REJECTED** |
| Model | Provider abstraction | **REQUIRED** |
| Ollama | Local inference | **VERIFIED** |
| llama.cpp | Android ARM64 | **VERIFIED** |
| llama.cpp | iOS XCFramework | **VERIFIED** |
| Chroma | Package availability | **VERIFIED** |
| Chroma | Sole source of truth | **REJECTED** |
| FTS5 | Deterministic fallback | **REQUIRED** |
| Embeddings | nomic-embed-text | **VERIFIED** |
| Plugins | Same-process trust | **REJECTED** |
| Plugins | Subprocess boundary | **REQUIRED** |
| File edits | Direct overwrite | **REJECTED** |
| File edits | Transactional/hash-checked | **REQUIRED** |
| Checkpoints | pickle deserialization | **REJECTED** |
| Checkpoints | Validated state (JSON + hash) | **REQUIRED** |
| Prompt injection | Output filter only | **REJECTED** |
| Prompt injection | Deterministic capability enforcement | **REQUIRED** |
| Network | Unrestricted URL fetch | **REJECTED** |
| Network | Explicit SSRF-safe capability | **REQUIRED** |
| Mobile | Android Termux route | **VIABLE** |
| Mobile | iOS Python dependency | **REJECTED** |
| Mobile | iOS native llama.cpp route | **VIABLE** |
| Performance | Universal fixed thresholds | **REJECTED** |
| Performance | Device/model profiles | **REQUIRED** |
| Runtime tests | Claimed passed (source roadmap) | **NOT VERIFIED** |
| Release | Evidence package | **REQUIRED** |

---

## 19. Release Roadmap Phase 0–8

| Phase | Name | Slices | Deliverable | Gate |
|-------|------|--------|-------------|------|
| **0** | Foundation | 0–3 | Secure repository foundation | Tests + configuration + workspace security + audit log |
| **1** | Model and Tools | 4–8 | Safe model-to-tool execution loop | Model cannot bypass policy; edits transactional |
| **2** | Knowledge | 9–16 | Local project-aware retrieval | FTS without Chroma; malicious docs cannot obtain authority |
| **3** | Agent | 17–21 | Recoverable coding agent | Mock-model agent completes deterministic fixtures |
| **4** | Extensibility | 18–19 | Isolated plugin system | Malicious plugins cannot escape capability boundary |
| **5** | Security | 22 | Automated adversarial security suite | Zero critical/high release-blocking findings |
| **6** | Evaluation | 23–26 | Reliability, augmentation, model, E2E benchmarks | Results reproducible; stored as artifacts |
| **7** | Mobile | 27–30 | Android and iOS deployment tracks | One real device per platform completes minimum offline workflow |
| **8** | Release Engineering | 31–36 | v1.0.0 release candidate and public release | All evidence collected; independently reproducible |

### 19.1 Phase Dependency Graph

```
Phase 0 ──► Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 6
                │              │         │
                │              │         ├──► Phase 4
                │              │         │
                │              │         └──► Phase 5
                │              │
                └──────────────┴──► Phase 7 (after Phase 3 minimum)
                                          │
                                          ▼
                                    Phase 8
```

### 19.2 Phase Exit Evidence

Each phase exit requires:

1. All slices in range: acceptance criteria PASS with evidence records.
2. Phase gate script in CI (future: `agent phase-gate --phase N`).
3. Updated `manifest/local_coding_agent_tracking.json` phase status.
4. Evidence subdirectory populated per Section 20.

---

## 20. Evidence Package Structure

```
evidence/
├── dependency/
│   └── model-matrix.json
├── security/
│   ├── prompt-injection/
│   ├── path-traversal/
│   └── ssrf/
├── reliability/
│   └── crash-recovery/
├── performance/
│   ├── desktop/
│   ├── android/
│   └── ios/
├── knowledge/
│   └── ingestion/
├── integration/
│   └── coding-tasks/
├── mobile/
│   ├── android/
│   └── ios/
└── release/
    ├── sbom/
    ├── checksums/
    └── test-report/
```

### 20.1 Evidence Package Rules

1. Every test produces at least one evidence record (Section 21).
2. Artifacts referenced by path relative to `evidence/`.
3. No evidence record without corresponding artifact file.
4. RC validation (SLICE 35) archives entire `evidence/` tree with manifest checksum.
5. Third-party reproduction uses lockfile + `scripts/reproduce_evidence.sh` (SLICE 35).

---

## 21. Evidence Record Format

### 21.1 Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `test_id` | string | yes | Stable identifier (e.g. SEC-PATH-001) |
| `name` | string | yes | Human-readable test name |
| `date` | string | yes | ISO-8601 date |
| `software_version` | string | yes | Agent semver or git tag |
| `platform` | string | yes | linux, macos, android, ios |
| `result` | string | yes | PASS, FAIL, SKIP |
| `artifacts` | array[string] | yes | Paths to log/json/screenshot files |

### 21.2 Example Record

```json
{
  "test_id": "SEC-PATH-001",
  "name": "workspace path traversal",
  "date": "2026-08-08",
  "software_version": "0.1.0",
  "platform": "linux",
  "result": "PASS",
  "artifacts": [
    "evidence/security/path-traversal/logs/SEC-PATH-001.json"
  ]
}
```

### 21.3 Example Artifact (SEC-PATH-001.json)

```json
{
  "test_id": "SEC-PATH-001",
  "attempts": [
    {"path": "../../../etc/passwd", "denied": true, "reason": "PATH_DENIED"},
    {"path": "src/../../../etc/passwd", "denied": true, "reason": "PATH_DENIED"},
    {"path": "src/%2e%2e/etc/passwd", "denied": true, "reason": "PATH_DENIED"}
  ],
  "audit_events_emitted": 3,
  "duration_ms": 12
}
```

---

## 22. Current Web Evidence Used

Public sources consulted during audit (2026-08-08). URLs are authoritative as of review date; re-verify before public release (Section 25).

| Topic | Source | Finding | Status |
|-------|--------|---------|--------|
| Ollama project | https://ollama.com/ | Active local inference runtime with model library | VERIFIED |
| Ollama Qwen3-Coder models | https://ollama.com/library/qwen3-coder | Lists 30B-class and larger variants; not 7B as specified | INVALID_AS_WRITTEN for 7B |
| llama.cpp | https://github.com/ggerganov/llama.cpp | GGUF inference; mobile build documentation | VERIFIED |
| llama.cpp Android | llama.cpp docs / community ARM64 builds | ARM64 Android inference path documented | VERIFIED |
| ChromaDB | https://www.trychroma.com/ | Active vector database project | VERIFIED (existence) |
| nomic-embed-text | Ollama library / Nomic documentation | Embedding model available via Ollama | VERIFIED |
| SQLite FTS5 | https://www.sqlite.org/fts5.html | FTS5 extension documented and stable | VERIFIED |
| Qwen3 model family | Alibaba / Hugging Face announcements | Qwen3 family exists; SKU matrix varies by host | PARTIALLY_VERIFIED |
| iOS Python | Apple platform guidelines | No supported iOS Python for App Store agent core | REJECTED for iOS |
| Android Termux | Termux project | Python environment on Android via Termux | PARTIALLY_VERIFIED |
| Prompt injection defenses | OWASP LLM Top 10 (2025) | Capability enforcement recommended over output filtering alone | PARTIALLY_VERIFIED |
| SSRF controls | OWASP SSRF guidance | Private IP block, redirect validation standard practice | PARTIALLY_VERIFIED |

### 22.1 Evidence Gaps Requiring Runtime

| Gap | Required action | Slice |
|-----|-----------------|-------|
| Mobile device inference latency | Physical device benchmark | SLICE 27, 31 |
| Security advisory scan | Dependency audit tool run | SLICE 34 |
| End-to-end coding task pass rate | Execute 10 tasks with evidence | SLICE 26 |
| Checkpoint recovery under crash | Chaos test execution | SLICE 21 |
| Plugin boundary escape test | Malicious plugin fixture | SLICE 19, 22 |

---

## 23. Final Engineering Verdict

### 23.1 Verdict Statement

| Field | Value |
|-------|-------|
| **Implement?** | **Yes** — model-agnostic local-first coding agent |
| **Source roadmap literal?** | **No** — reject fixed Qwen3-Coder-7B and Chroma-primary design |
| **Go decision allowed?** | **No** — runtime evidence not yet collected |
| **Next action** | Begin **Phase 0 / SLICE 0** with engineering contract and test runner |

### 23.2 Success Criteria for v1.0.0

1. All 37 slices: acceptance PASS with evidence records.
2. All three implementability review conditions satisfied with proof.
3. Final acceptance matrix: no REJECTED row remains applicable to implementation.
4. Public release gate: six checks at minimum PARTIALLY_VERIFIED with runtime evidence for check 6.
5. Evidence package independently reproducible (SLICE 35).

### 23.3 Explicit Non-Goals for v1.0.0

| Non-goal | Reason |
|----------|--------|
| Cloud-hosted inference | Local-first scope |
| Arbitrary shell execution | HIGH_RISK; defer past v1 |
| iOS Python runtime | Platform rejection |
| Single fixed model SKU | Model matrix required |
| Model-as-judge-only acceptance | Evidence-based acceptance required |
| Pickle checkpoints | Security rejection |

---

## 24. Implementation Rule Pipeline

### 24.1 Slice Completion Pipeline

A slice is **not complete** until every step executes:

```
SPECIFY → IMPLEMENT → UNIT TEST → SECURITY TEST → INTEGRATION TEST
    → DOCUMENT → UPDATE PROJECT_STATE.md → COMMIT → NEXT SLICE
```

### 24.2 Step Definitions

| Step | Requirement |
|------|-------------|
| SPECIFY | Acceptance criteria written in slice section; interfaces defined |
| IMPLEMENT | Code merged to feature branch |
| UNIT TEST | pytest coverage for new modules |
| SECURITY TEST | Adversarial tests where applicable (from SLICE 22 onward, retroactive for security slices) |
| INTEGRATION TEST | Cross-module test with MockProvider |
| DOCUMENT | Update relevant doc in `docs/` |
| UPDATE PROJECT_STATE.md | Phase/slice status in tracking manifest |
| COMMIT | Atomic commit with slice id in message |
| NEXT SLICE | Only after evidence record exists |

### 24.3 Core Rule

> **A slice is complete only when acceptance criteria have executable evidence — not when code exists.**

### 24.4 Forbidden Completion Signals

| Signal | Why forbidden |
|--------|---------------|
| "Code merged" without tests | No executable evidence |
| "Works on my machine" without artifact | Not reproducible |
| Model self-assessment PASS | Model is not verifier |
| Skipping SECURITY TEST for write tools | Release-blocking gap |
| Proceeding with failing prior slice | Dependency chain violation |

---

## 25. Public Release Gate

Six checks must be evaluated before public release (v1.0.0). **Go decision allowed only when all checks are VERIFIED or PARTIALLY_VERIFIED with documented scope — never UNVERIFIED for security advisories.**

| # | Check | Status (2026-08-08) | Requirement for GO |
|---|-------|---------------------|-------------------|
| 1 | Model recommendations current with evidence | `PARTIALLY_VERIFIED` | Model matrix JSON in evidence package; each SKU cited |
| 2 | Active repositories verified | `PARTIALLY_VERIFIED` | Dependency repos tagged at RC freeze |
| 3 | Package licenses documented | `PARTIALLY_VERIFIED` | SPDX list in SBOM (SLICE 33) |
| 4 | Security advisories reviewed | `UNVERIFIED` | Zero unmitigated critical/high in dependencies |
| 5 | Current prompt injection defenses documented | `PARTIALLY_VERIFIED` | THREAT_MODEL.md matches SLICE 22 harness |
| 6 | Current mobile OS testing on real devices | `UNEXECUTED_REQUIRES_RUNTIME` | One Android + one iOS device evidence minimum |

### 25.1 Public Release Gate Decision

```
go_decision_allowed = false  (as of 2026-08-08)
```

### 25.2 Pre-Release Checklist

- [ ] SLICE 36 acceptance: git tag v1.0.0 with checksums
- [ ] Evidence package archived and checksum published
- [ ] SECURITY.md and vulnerability disclosure process live
- [ ] All six public release checks documented with evidence paths
- [ ] Post-release monitoring plan (crash reports, advisory subscription)

---

## Document Control

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0.0 | 2026-08-08 | Engineering audit | Initial deliverable |

**Companion artifacts:**

- Frontier spec: `frontier/roadmap/local_coding_agent.fr`
- Tracking manifest: `manifest/local_coding_agent_tracking.json`
- Roadmap index: `docs/roadmap.fr`

---

*End of document.*
