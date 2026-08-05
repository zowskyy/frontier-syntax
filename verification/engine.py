#!/usr/bin/env python3
"""
verification/engine.py - Unified Verification Engine v3.0

Improvements over build_truth.sh:
- Python orchestration with incremental caching
- Property-based testing
- Parallel independent phases
- Optional Docker sandbox with host comparison
- Mandatory Coq in CI mode
- Honest differential checks (hash parity, WASM build, host vs container)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from verification.property_tests import run_property_suite

SAMPLE_FILES = [
    "examples/sample.fr",
    "examples/sample_v2.fr",
    "examples/v2_parser_test.fr",
    "examples/auto_optimize.fr",
]


@dataclass
class VerificationConfig:
    project_root: Path = field(default_factory=Path.cwd)
    quick: bool = False
    ci: bool = False
    verbose: bool = False
    phases: List[str] = field(default_factory=lambda: ["all"])
    cache_dir: Path = Path(".verification_cache")
    max_workers: int = 4
    timeout: int = 600
    seed: int = 42
    no_cache: bool = False


class VerificationCache:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_file = cache_dir / "manifest.json"
        self.manifest = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.manifest_file.exists():
            return json.loads(self.manifest_file.read_text(encoding="utf-8"))
        return {}

    def _save(self) -> None:
        self.manifest_file.write_text(json.dumps(self.manifest, indent=2) + "\n", encoding="utf-8")

    def compute_digest(self, phase: str, inputs: List[Path]) -> str:
        hasher = hashlib.sha256()
        hasher.update(phase.encode())
        hasher.update(str(self.manifest.get("_seed", 42)).encode())
        try:
            commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=inputs[0].parent if inputs else ".",
                text=True,
            ).strip()
            hasher.update(commit.encode())
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        for path in sorted(inputs):
            if not path.exists() or not path.is_file():
                continue
            hasher.update(str(path).encode())
            hasher.update(path.read_bytes())
        return hasher.hexdigest()

    def get(self, phase: str, digest: str) -> Optional[Dict[str, Any]]:
        entry = self.manifest.get(phase)
        if not entry:
            return None
        if entry.get("digest") != digest:
            return None
        return entry.get("result")

    def set(self, phase: str, digest: str, result: Dict[str, Any]) -> None:
        self.manifest[phase] = {
            "digest": digest,
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._save()


class VerificationEngine:
    PHASE_INPUTS: Dict[str, List[str]] = {
        "environment": [],
        "proof": ["proofs"],
        "fuzz": ["src", "Cargo.toml", "Cargo.lock"],
        "emulate": SAMPLE_FILES,
        "compile": ["Cargo.toml", "Cargo.lock", "src"],
        "sandbox": SAMPLE_FILES,
        "compare": SAMPLE_FILES,
        "certify": [],
        "report": [],
    }

    def __init__(self, config: VerificationConfig):
        self.config = config
        self.config.project_root = self.config.project_root.resolve()
        self.cache = VerificationCache(self.config.project_root / self.config.cache_dir)
        self.cache.manifest["_seed"] = self.config.seed
        self.results: Dict[str, Dict[str, Any]] = {}
        self.start_time = time.time()
        self.frontier_bin = self._find_or_build_frontier()
        self.reports_dir = self.config.project_root / "verification" / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.cert_dir = self.config.project_root / "proof" / "certificates"
        self.cert_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> bool:
        self._banner()
        phases = self._resolve_phases()
        groups = self._phase_groups(phases)

        for group in groups:
            if len(group) == 1:
                phase = group[0]
                self.results[phase] = self._run_phase(phase)
                self._print_result(phase, self.results[phase])
            else:
                with ThreadPoolExecutor(max_workers=min(self.config.max_workers, len(group))) as pool:
                    futures = {pool.submit(self._run_phase, phase): phase for phase in group}
                    for future in as_completed(futures):
                        phase = futures[future]
                        result = future.result()
                        self.results[phase] = result
                        self._print_result(phase, result)

        certify = self._phase_certify()
        self.results["certify"] = certify
        self._print_result("certify", certify)

        report = self._phase_report()
        self.results["report"] = report
        self._print_result("report", report)

        return self._summary()

    def _banner(self) -> None:
        print("\n" + "=" * 60)
        print("FRONTIER VERIFICATION ENGINE v3.0")
        print(f"Project: {self.config.project_root}")
        print(f"Mode: {'quick' if self.config.quick else 'full'}")
        print(f"CI: {'on' if self.config.ci else 'off'}")
        print(f"Seed: {self.config.seed}")
        print("=" * 60 + "\n")

    def _resolve_phases(self) -> List[str]:
        all_phases = [
            "environment",
            "proof",
            "fuzz",
            "emulate",
            "compile",
            "sandbox",
            "compare",
        ]
        if self.config.quick:
            return ["environment", "proof", "fuzz", "emulate", "compile", "compare"]
        if "all" in self.config.phases:
            return all_phases
        return [phase.strip() for phase in self.config.phases if phase.strip()]

    def _phase_groups(self, phases: List[str]) -> List[List[str]]:
        order = [
            ["environment"],
            [phase for phase in ["proof", "fuzz", "emulate", "compile"] if phase in phases],
            [phase for phase in ["sandbox"] if phase in phases],
            [phase for phase in ["compare"] if phase in phases],
        ]
        return [group for group in order if group]

    def _inputs_for_phase(self, phase: str) -> List[Path]:
        root = self.config.project_root
        paths: List[Path] = []
        for rel in self.PHASE_INPUTS.get(phase, []):
            path = root / rel
            if path.is_dir():
                paths.extend(sorted(p for p in path.rglob("*") if p.is_file()))
            else:
                paths.append(path)
        return paths

    def _run_phase(self, phase: str) -> Dict[str, Any]:
        digest = self.cache.compute_digest(phase, self._inputs_for_phase(phase))
        if not self.config.no_cache and not self.config.ci:
            cached = self.cache.get(phase, digest)
            if cached is not None:
                print(f"  cache hit: {phase}")
                return cached

        handlers: Dict[str, Callable[[], Dict[str, Any]]] = {
            "environment": self._phase_environment,
            "proof": self._phase_proof,
            "fuzz": self._phase_fuzz,
            "emulate": self._phase_emulate,
            "compile": self._phase_compile,
            "sandbox": self._phase_sandbox,
            "compare": self._phase_compare,
        }
        result = handlers[phase]()
        self.cache.set(phase, digest, result)
        return result

    def _find_or_build_frontier(self) -> Path:
        candidates = [
            self.config.project_root / "target" / "release" / "frontier",
            self.config.project_root / "target" / "debug" / "frontier",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        print("  building frontier binary...")
        subprocess.run(
            ["cargo", "build", "--release", "--bin", "frontier"],
            cwd=self.config.project_root,
            check=True,
        )
        return self.config.project_root / "target" / "release" / "frontier"

    def _phase_environment(self) -> Dict[str, Any]:
        info = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": self._detect_environment(),
            "git_commit": self._git_commit(),
            "system": self._system_info(),
            "tools": self._tool_versions(),
            "frontier_bin": str(self.frontier_bin),
            "seed": self.config.seed,
        }
        path = self.reports_dir / "environment_detection.json"
        path.write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
        return {"success": True, **info}

    def _phase_proof(self) -> Dict[str, Any]:
        proof_dir = self.config.project_root / "proofs"
        proof_files = sorted(proof_dir.glob("*.v"))
        if not proof_files:
            return {"success": False, "error": f"No Coq proofs found in {proof_dir}"}

        try:
            coq_version = subprocess.check_output(["coqc", "--version"], text=True).strip().split("\n")[0]
        except (subprocess.CalledProcessError, FileNotFoundError):
            if self.config.ci:
                return {"success": False, "error": "Coq is required in CI mode", "mandatory": True}
            return {"success": True, "skipped": True, "reason": "coqc not installed", "proof_files": [p.name for p in proof_files]}

        results = []
        for proof_file in proof_files:
            proc = subprocess.run(
                ["coqc", str(proof_file)],
                cwd=self.config.project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )
            entry = {
                "file": proof_file.name,
                "success": proc.returncode == 0,
                "output": proc.stdout if proc.returncode == 0 else proc.stderr[-500:],
            }
            results.append(entry)
            if proc.returncode != 0:
                return {"success": False, "error": f"Proof failed: {proof_file.name}", "proofs": results}

        return {"success": True, "proofs": results, "coq_version": coq_version, "count": len(results)}

    def _phase_fuzz(self) -> Dict[str, Any]:
        iterations = 500 if self.config.quick else 10_000
        property_result = run_property_suite(
            self.frontier_bin,
            max_tests=100 if self.config.quick else 500,
            seed=self.config.seed,
            project_root=self.config.project_root,
        )
        if not property_result["success"]:
            return {
                "success": False,
                "error": "Property-based tests failed",
                "property_tests": property_result,
            }

        proc = subprocess.run(
            [str(self.frontier_bin), "fuzz", str(iterations)],
            cwd=self.config.project_root,
            capture_output=True,
            text=True,
            timeout=120 if self.config.quick else 600,
        )
        if proc.returncode != 0:
            return {
                "success": False,
                "error": "Built-in fuzzer failed",
                "output": proc.stdout + proc.stderr,
                "property_tests": property_result,
            }

        sample_hashes = {}
        for rel in SAMPLE_FILES[:3]:
            path = self.config.project_root / rel
            if not path.exists():
                continue
            h1 = self._hash_file(path)
            h2 = self._hash_file(path)
            if h1 != h2:
                return {"success": False, "error": f"Non-deterministic hash on {rel}", "hash": h1}
            sample_hashes[rel] = h1

        return {
            "success": True,
            "iterations": iterations,
            "seed": self.config.seed,
            "property_tests": property_result,
            "sample_hashes": sample_hashes,
            "fuzz_output": proc.stdout.strip(),
        }

    def _phase_emulate(self) -> Dict[str, Any]:
        iterations = 100 if self.config.quick else 1000
        times: List[float] = []
        successes = 0
        programs = self._emulation_programs()

        for index in range(iterations):
            source, rel = programs[index % len(programs)]
            start = time.perf_counter()
            with self._temp_source(source, suffix=".fr") as path:
                proc = subprocess.run(
                    [str(self.frontier_bin), "parse", str(path)],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
            elapsed_ms = (time.perf_counter() - start) * 1000
            times.append(elapsed_ms)
            if proc.returncode == 0:
                successes += 1

        success_rate = successes / iterations if iterations else 0.0
        stats = {
            "iterations": iterations,
            "success_rate": success_rate,
            "mean_ms": statistics.mean(times) if times else 0.0,
            "median_ms": statistics.median(times) if times else 0.0,
            "p95_ms": statistics.quantiles(times, n=20)[18] if len(times) >= 20 else max(times, default=0.0),
            "stdev_ms": statistics.stdev(times) if len(times) > 1 else 0.0,
            "min_ms": min(times) if times else 0.0,
            "max_ms": max(times) if times else 0.0,
            "programs": [rel for _, rel in programs],
        }
        (self.reports_dir / "emulation_stats.json").write_text(
            json.dumps(stats, indent=2) + "\n",
            encoding="utf-8",
        )
        if success_rate < 0.95:
            return {"success": False, "error": f"Success rate {success_rate:.2%} below 95%", **stats}
        return {"success": True, **stats}

    def _phase_compile(self) -> Dict[str, Any]:
        if self.config.quick:
            builds = [self._cargo_build(None, None)]
            wasm = self._cargo_build(None, "wasm32-unknown-unknown")
            builds.append(wasm)
        else:
            toolchains = ["stable", "beta", "nightly"]
            targets = ["x86_64-unknown-linux-gnu", "wasm32-unknown-unknown"]
            builds = []
            for toolchain in toolchains:
                for target in targets:
                    builds.append(self._cargo_build(toolchain, target))

        failed = [build for build in builds if not build["success"]]
        if failed and self.config.ci:
            return {"success": False, "error": "Compiler matrix failures", "builds": builds}
        if failed and not self.config.ci:
            print(f"  warning: {len(failed)} compiler matrix builds failed (non-CI mode)")

        return {
            "success": all(build["success"] for build in builds[:2]) if self.config.quick else len(failed) == 0,
            "builds": builds,
            "passing": sum(1 for build in builds if build["success"]),
            "total": len(builds),
        }

    def _phase_sandbox(self) -> Dict[str, Any]:
        if not self._docker_available():
            if self.config.ci:
                return {"success": False, "error": "Docker required in CI mode for sandbox phase"}
            return {"success": True, "skipped": True, "reason": "docker not available"}

        sample = self.config.project_root / "examples" / "sample.fr"
        if not sample.exists():
            return {"success": False, "error": "examples/sample.fr missing"}

        host_hash = self._hash_file(sample)
        docker_hash = self._docker_hash(sample)
        if docker_hash is None:
            return {"success": False, "error": "Docker sandbox execution failed"}

        profile = {
            "environment": self._detect_environment(),
            "host_hash": host_hash,
            "docker_hash": docker_hash,
            "matched": host_hash == docker_hash,
            "image": "frontier-verification-sandbox",
        }
        profiles_dir = self.config.project_root / "verification" / "sandbox_profiles"
        profiles_dir.mkdir(parents=True, exist_ok=True)
        profile_path = profiles_dir / f"{profile['environment']}_docker.json"
        profile_path.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")

        sandbox_results = {
            "environment": profile["environment"],
            "host_hash": host_hash,
            "docker_hash": docker_hash,
            "matched": profile["matched"],
            "isolated": True,
        }
        (self.reports_dir / "sandbox_results.json").write_text(
            json.dumps(sandbox_results, indent=2) + "\n",
            encoding="utf-8",
        )
        if not profile["matched"]:
            return {"success": False, "error": "Host and Docker hash mismatch", **profile}
        return {"success": True, **profile}

    def _phase_compare(self) -> Dict[str, Any]:
        emulate_stats = self._read_json(self.reports_dir / "emulation_stats.json")
        if not emulate_stats:
            return {"success": False, "error": "Missing emulation stats"}

        sample = self.config.project_root / "examples" / "sample.fr"
        local_times = []
        for _ in range(20):
            start = time.perf_counter()
            subprocess.run(
                [str(self.frontier_bin), "parse", str(sample)],
                capture_output=True,
                text=True,
                timeout=5,
            )
            local_times.append((time.perf_counter() - start) * 1000)
        local_median = statistics.median(local_times)
        formal_median = emulate_stats.get("median_ms", local_median)

        time_delta_pct = self._percent_delta(formal_median, local_median)
        tolerance = 50.0
        time_ok = abs(time_delta_pct) <= tolerance

        wasm_path = (
            self.config.project_root
            / "target"
            / "wasm32-unknown-unknown"
            / "release"
            / "frontier.wasm"
        )
        wasm_built = wasm_path.exists()

        comparison = {
            "environment": self._detect_environment(),
            "formal_metrics": {"execution_time_ms": formal_median},
            "sandbox_metrics": {"execution_time_ms": local_median},
            "time_delta_percent": time_delta_pct,
            "within_tolerance": time_ok,
            "wasm_built": wasm_built,
            "tolerance_percent": tolerance,
            "truthful": time_ok and wasm_built,
            "reason": "Parse timing consistent and WASM artifact present" if time_ok and wasm_built else "Comparison thresholds not met",
        }
        (self.reports_dir / "comparison_report.json").write_text(
            json.dumps(comparison, indent=2) + "\n",
            encoding="utf-8",
        )
        if self.config.ci and not comparison["truthful"]:
            return {"success": False, **comparison}
        return {"success": comparison["truthful"], **comparison}

    def _phase_certify(self) -> Dict[str, Any]:
        cert = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "git_commit": self._git_commit(),
            "environment": self._detect_environment(),
            "seed": self.config.seed,
            "phases": {
                phase: {
                    "status": "PASSED" if result.get("success") else "FAILED",
                    "skipped": result.get("skipped", False),
                }
                for phase, result in self.results.items()
                if isinstance(result, dict)
            },
            "overall_status": "PASSED"
            if all(result.get("success", False) for result in self.results.values())
            else "FAILED",
            "duration_seconds": round(time.time() - self.start_time, 2),
        }
        cert_file = self.cert_dir / f"certificate_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        cert_file.write_text(json.dumps(cert, indent=2) + "\n", encoding="utf-8")
        cert_hash = hashlib.sha256(cert_file.read_bytes()).hexdigest()
        (cert_file.parent / f"{cert_file.name}.sha256").write_text(
            f"{cert_hash}  {cert_file.name}\n",
            encoding="utf-8",
        )
        truth_file = self.config.project_root / f"truth_certificate_{cert_file.stem.split('_', 1)[1]}.txt"
        truth_file.write_text(self._truth_certificate_text(cert, cert_hash), encoding="utf-8")
        truth_hash = hashlib.sha256(truth_file.read_bytes()).hexdigest()
        (self.config.project_root / f"{truth_file.name}.sha256").write_text(
            f"{truth_hash}  {truth_file.name}\n",
            encoding="utf-8",
        )
        return {"success": cert["overall_status"] == "PASSED", "certificate": str(cert_file), "hash": cert_hash}

    def _phase_report(self) -> Dict[str, Any]:
        passed = sum(1 for result in self.results.values() if result.get("success"))
        failed = sum(1 for result in self.results.values() if not result.get("success") and not result.get("skipped"))
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "git_commit": self._git_commit(),
            "overall_status": "PASSED" if all(result.get("success", False) for result in self.results.values()) else "FAILED",
            "summary": {
                "total": len(self.results),
                "passed": passed,
                "failed": failed,
                "duration_seconds": round(time.time() - self.start_time, 2),
            },
            "phases": self.results,
        }
        report_file = self.reports_dir / f"final_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        report_file.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        return {"success": report["overall_status"] == "PASSED", "report": str(report_file)}

    def _cargo_build(self, toolchain: Optional[str], target: Optional[str]) -> Dict[str, Any]:
        cmd = ["cargo", "build", "--workspace"]
        if target:
            cmd.extend(["--target", target])
            if not self.config.quick:
                cmd.append("--release")
        label = f"{toolchain or 'active'}/{target or 'host'}"
        env = os.environ.copy()
        if toolchain:
            env["RUSTUP_TOOLCHAIN"] = toolchain
            subprocess.run(
                ["rustup", "target", "add", target] if target else ["true"],
                cwd=self.config.project_root,
                capture_output=True,
                text=True,
            )
        proc = subprocess.run(
            cmd,
            cwd=self.config.project_root,
            capture_output=True,
            text=True,
            timeout=300,
            env=env,
        )
        return {
            "toolchain": toolchain or "active",
            "target": target or "host",
            "label": label,
            "success": proc.returncode == 0,
            "output_tail": (proc.stdout + proc.stderr)[-300:],
        }

    def _docker_available(self) -> bool:
        try:
            subprocess.run(["docker", "version"], capture_output=True, check=True, timeout=10)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _docker_hash(self, sample: Path) -> Optional[str]:
        dockerfile = self.config.project_root / ".build_truth_sandbox" / "Dockerfile"
        dockerfile.parent.mkdir(parents=True, exist_ok=True)
        dockerfile.write_text(
            "\n".join(
                [
                    "FROM rust:1.89-slim-bookworm",
                    "WORKDIR /app",
                    "COPY . .",
                    "RUN cargo build --release --bin frontier",
                    'ENTRYPOINT ["./target/release/frontier"]',
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        image = "frontier-verification-sandbox"
        build = subprocess.run(
            ["docker", "build", "-t", image, "-f", str(dockerfile), str(self.config.project_root)],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if build.returncode != 0:
            return None
        rel = sample.relative_to(self.config.project_root)
        run = subprocess.run(
            ["docker", "run", "--rm", image, "hash", str(rel)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if run.returncode != 0:
            return None
        return run.stdout.strip()

    def _hash_file(self, path: Path) -> str:
        proc = subprocess.run(
            [str(self.frontier_bin), "hash", str(path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"hash failed for {path}: {proc.stderr}")
        return proc.stdout.strip()

    def _emulation_programs(self) -> List[Tuple[str, str]]:
        programs: List[Tuple[str, str]] = []
        for rel in SAMPLE_FILES:
            path = self.config.project_root / rel
            if path.exists():
                programs.append((path.read_text(encoding="utf-8"), rel))
        if not programs:
            fallback = self.config.project_root / "examples" / "sample.fr"
            programs.append((fallback.read_text(encoding="utf-8"), "examples/sample.fr"))
        return programs

    def _temp_source(self, source: str, suffix: str):
        from contextlib import contextmanager
        import tempfile

        @contextmanager
        def manager():
            with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False) as handle:
                handle.write(source)
                path = Path(handle.name)
            try:
                yield path
            finally:
                path.unlink(missing_ok=True)

        return manager()

    def _detect_environment(self) -> str:
        if os.environ.get("GITHUB_ACTIONS"):
            return "github_actions"
        if os.environ.get("CODESPACES") or os.environ.get("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN"):
            return "github_codespaces"
        if os.environ.get("CURSOR_AGENT_ID") or os.environ.get("CURSOR_AGENT") or Path("/.cursor").exists():
            return "cursor"
        if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_AGENT"):
            return "claude"
        return "local_development"

    def _git_commit(self) -> str:
        try:
            return subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=self.config.project_root,
                text=True,
            ).strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "unknown"

    def _system_info(self) -> Dict[str, str]:
        return {
            "os": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "cpu_count": str(os.cpu_count() or 0),
            "hostname": platform.node(),
        }

    def _tool_versions(self) -> Dict[str, str]:
        versions: Dict[str, str] = {}
        commands = {
            "rustc": ["rustc", "--version"],
            "cargo": ["cargo", "--version"],
            "python": [sys.executable, "--version"],
            "git": ["git", "--version"],
            "coq": ["coqc", "--version"],
            "docker": ["docker", "--version"],
        }
        for name, cmd in commands.items():
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                versions[name] = proc.stdout.strip().split("\n")[0] if proc.stdout else proc.stderr.strip()
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                versions[name] = "unavailable"
        return versions

    def _read_json(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _percent_delta(self, formal: float, sandbox: float) -> float:
        if formal == 0:
            return 0.0
        return round(((sandbox - formal) / formal) * 100, 2)

    def _truth_certificate_text(self, cert: Dict[str, Any], cert_hash: str) -> str:
        lines = [
            "=" * 63,
            "TRUTH VERIFICATION CERTIFICATE (ENGINE v3.0)",
            "=" * 63,
            "",
            f"Timestamp: {cert['timestamp']}",
            f"Git Commit: {cert['git_commit']}",
            f"Environment: {cert['environment']}",
            f"Seed: {cert['seed']}",
            f"Overall: {cert['overall_status']}",
            "",
            "Phases:",
        ]
        for phase, meta in cert["phases"].items():
            status = meta["status"]
            if meta.get("skipped"):
                status = "SKIPPED"
            lines.append(f"  - {phase}: {status}")
        lines.extend(
            [
                "",
                f"Certificate SHA-256: {cert_hash}",
                "=" * 63,
            ]
        )
        return "\n".join(lines) + "\n"

    def _print_result(self, phase: str, result: Dict[str, Any]) -> None:
        if result.get("skipped"):
            mark = "SKIP"
        elif result.get("success"):
            mark = "PASS"
        else:
            mark = "FAIL"
        print(f"  [{mark}] {phase}")

    def _summary(self) -> bool:
        ok = all(result.get("success", False) for result in self.results.values())
        print("\n" + "=" * 60)
        print(f"VERIFICATION {'PASSED' if ok else 'FAILED'}")
        print(f"Duration: {time.time() - self.start_time:.2f}s")
        print(f"Phases: {len(self.results)}")
        print("=" * 60 + "\n")
        return ok


def main() -> None:
    parser = argparse.ArgumentParser(description="Frontier Verification Engine v3.0")
    parser.add_argument("--quick", action="store_true", help="Quick verification (~1 min)")
    parser.add_argument("--ci", action="store_true", help="CI mode (fail-fast, mandatory gates)")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--phases", default="all", help="Comma-separated phases")
    parser.add_argument("--cache-dir", default=".verification_cache", help="Cache directory")
    parser.add_argument("--workers", type=int, default=4, help="Parallel workers")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--no-cache", action="store_true", help="Disable incremental cache")
    args = parser.parse_args()

    config = VerificationConfig(
        project_root=Path.cwd(),
        quick=args.quick,
        ci=args.ci,
        verbose=args.verbose,
        phases=args.phases.split(","),
        cache_dir=Path(args.cache_dir),
        max_workers=args.workers,
        seed=args.seed,
        no_cache=args.no_cache,
    )
    engine = VerificationEngine(config)
    sys.exit(0 if engine.run() else 1)


if __name__ == "__main__":
    main()
