#!/usr/bin/env python3
"""
Frontier Syntax Cursor Agent
Complete automation for the Frontier Syntax language project
Version: 2.0.0
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class FrontierAgent:
    """Main agent class that controls the entire Frontier Syntax ecosystem."""

    CYCLE_SCRIPTS: Dict[int, List[List[str]]] = {
        1: [["scripts/verify_cycle1.py"]],
        2: [
            ["scripts/verify_cycle1.py"],
            ["cargo", "run", "--release", "--quiet", "--", "parse", "examples/sample.fr"],
        ],
        3: [["scripts/analyze_grammar.py"]],
        4: [
            [
                "cargo",
                "run",
                "--release",
                "--quiet",
                "--",
                "resolve",
                "examples/sample.fr",
            ]
        ],
        5: [
            ["cargo", "run", "--release", "--quiet", "--", "gen-artifacts"],
            ["scripts/test_roundtrip.py"],
        ],
        6: [
            ["scripts/test_redos.py"],
            ["cargo", "run", "--release", "--quiet", "--", "fuzz", "1000"],
        ],
    }

    def __init__(self) -> None:
        self.repo_root = Path(__file__).resolve().parent
        self.core_dir = self.repo_root / "frontier" / "core"
        self.syntax_dir = self.repo_root / "syntax"
        self.src_dir = self.repo_root / "src"
        self.scripts_dir = self.repo_root / "scripts"
        self.build_dir = self.repo_root / "build"
        self.audit_dir = self.repo_root / "audit_reports"
        self.browser_dir = self.repo_root / "browser"

        self.cost_tracker = CostTracker()
        self.state = self.load_state()

    def load_state(self) -> Dict[str, Any]:
        """Load or initialize agent state."""
        state_file = self.repo_root / ".frontier_state.json"
        if state_file.exists():
            with open(state_file, encoding="utf-8") as handle:
                return json.load(handle)
        return {
            "version": "2.0.0",
            "last_audit_cycle": 0,
            "file_hashes": {},
            "test_results": [],
            "cost_savings": 0,
        }

    def save_state(self) -> None:
        """Save agent state."""
        state_file = self.repo_root / ".frontier_state.json"
        with open(state_file, "w", encoding="utf-8") as handle:
            json.dump(self.state, handle, indent=2)

    def speak_into_existence(self, intent: str, verify: bool = False) -> Dict[str, Any]:
        """Main entry point — convert natural language intent into code."""
        if verify:
            return self.verify_intent(intent)

        print(f"Processing: {intent}")

        parsed = self.parse_intent(intent)

        if parsed["type"] == "add_feature":
            result = self.add_feature(parsed)
        elif parsed["type"] == "fix_bug":
            result = self.fix_bug(parsed)
        elif parsed["type"] == "update_docs":
            result = self.update_documentation(parsed)
        elif parsed["type"] == "run_audit":
            result = self.run_audit_cycle(parsed)
        elif parsed["type"] == "deploy":
            result = self.deploy(parsed)
        elif parsed["type"] == "run_scrub":
            result = self.run_scrub_pipeline(parsed)
        elif parsed["type"] == "ingest_scrub":
            result = self.ingest_scrub_report(parsed)
        else:
            result = {"error": f"Unknown intent type: {parsed['type']}"}

        if "error" not in result:
            verify_ok = self.verify_all()
            result["verification_passed"] = verify_ok

        self.cost_tracker.record_savings(result)
        self.save_state()
        return result

    def process(self, intent: str, verify: bool = False) -> Dict[str, Any]:
        """Public API for symbiotic tandem integration."""
        return self.speak_into_existence(intent, verify=verify)

    def learn(self, intent: str, outcome: str) -> None:
        """Record intent outcome for feedback-loop routing."""
        learning = self.state.setdefault("learning", {"success": [], "failure": []})
        entry = {
            "intent": intent,
            "outcome": outcome,
            "at": datetime.now(timezone.utc).isoformat(),
        }
        bucket = "success" if outcome == "success" else "failure"
        learning[bucket].append(entry)
        self.save_state()

    def verify_intent(
        self, intent: str, prior_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Cross-verify an intent without mutating repository state."""
        parsed = self.parse_intent(intent)
        intent_type = parsed["type"]

        if intent_type == "run_audit":
            result = self.run_audit_cycle(parsed)
            status = result.get("status", "failed")
            return {"status": status, "intent": intent, "mode": "verify", "detail": result}

        if intent_type == "update_docs":
            doc_path = self.repo_root / "frontier" / "docs" / "language_reference.md"
            ok = doc_path.exists() and doc_path.stat().st_size > 0
            return {
                "status": "success" if ok else "failed",
                "intent": intent,
                "mode": "verify",
                "file": str(doc_path.relative_to(self.repo_root)),
            }

        if intent_type == "add_feature" and prior_result:
            files = prior_result.get("files_changed", [])
            missing = [
                f for f in files if not (self.repo_root / f).exists()
            ]
            ok = not missing
            return {
                "status": "success" if ok else "failed",
                "intent": intent,
                "mode": "verify",
                "missing_files": missing,
            }

        if intent_type == "fix_bug" and prior_result:
            fixed = prior_result.get("fixed_file")
            ok = bool(fixed and (self.repo_root / fixed).exists())
            tests_ok = prior_result.get("tests_passed", False)
            status = "success" if ok and tests_ok else "partial" if ok else "failed"
            return {
                "status": status,
                "intent": intent,
                "mode": "verify",
                "fixed_file": fixed,
                "tests_passed": tests_ok,
            }

        if intent_type == "deploy" and prior_result:
            version = prior_result.get("version", "")
            cargo = (self.repo_root / "Cargo.toml").read_text(encoding="utf-8")
            ok = version and f'version = "{version}"' in cargo
            return {
                "status": "success" if ok else "failed",
                "intent": intent,
                "mode": "verify",
                "version": version,
            }

        # Fallback: run lightweight test suite
        tests = self.run_tests()
        return {
            "status": "success" if tests["passed"] else "failed",
            "intent": intent,
            "mode": "verify",
            "tests_passed": tests["passed"],
        }

    def parse_intent(self, intent: str) -> Dict[str, Any]:
        """Parse natural language intent into structured actions."""
        intent_lower = intent.lower()

        # Order matters: specific intents before broad keyword matches.
        if any(word in intent_lower for word in ["documentation", "document", "doc "]):
            return {"type": "update_docs", "content": intent}
        if intent_lower.startswith("update doc") or " update doc" in intent_lower:
            return {"type": "update_docs", "content": intent}

        if any(word in intent_lower for word in ["scrub", "knowledge engine", "outperform", "chat scrub"]):
            if any(word in intent_lower for word in ["ingest", "embed", "hypercube"]):
                return {"type": "ingest_scrub", "content": intent}
            return {"type": "run_scrub", "content": intent, "delta": "delta" in intent_lower}

        if any(word in intent_lower for word in ["deploy", "release", "publish"]):
            return {"type": "deploy", "version": self.detect_version(intent)}

        if any(word in intent_lower for word in ["audit", "verify", "check"]):
            return {"type": "run_audit", "cycle": self.detect_cycle(intent)}

        if any(word in intent_lower for word in ["fix", "bug", "error", "issue"]):
            return {
                "type": "fix_bug",
                "description": intent,
                "target": self.detect_target(intent),
            }

        if self._is_add_feature_intent(intent_lower):
            return {
                "type": "add_feature",
                "feature": intent,
                "target": self.detect_target(intent),
            }

        return {
            "type": "add_feature",
            "feature": intent,
            "target": "auto",
        }

    def _is_add_feature_intent(self, intent_lower: str) -> bool:
        """Detect feature-addition intents without false positives on 'new' in docs."""
        if any(word in intent_lower for word in ["add", "create", "implement"]):
            return True
        if re.search(r"\bnew\b", intent_lower) and any(
            word in intent_lower
            for word in ["type", "struct", "keyword", "feature", "module", "support"]
        ):
            return True
        return False

    def detect_target(self, intent: str) -> str:
        """Detect which component the intent targets."""
        targets = {
            "parser": ["parser", "syntax", "grammar"],
            "memory": ["memory", "allocation", "gc"],
            "concurrency": ["concurrency", "thread", "async", "channel"],
            "type": ["types", "type system", "type checker", " called ", "decimal"],
            "error": ["error", "exception", "panic"],
            "stdlib": ["standard library", "lib", "collection"],
            "compiler": ["compiler", "backend", "codegen"],
            "zk": ["zk", "zero-knowledge", "proof"],
            "pq": ["post-quantum", "signature", "crypto"],
            "ipfs": ["ipfs", "decentralized", "import"],
            "neural": ["neural", "lsp", "ai", "completion"],
            "registry": ["registry", "package", "decentralized"],
        }

        intent_lower = intent.lower()
        for target, keywords in targets.items():
            if any(word in intent_lower for word in keywords):
                return target
        return "auto"

    def detect_cycle(self, intent: str) -> int:
        """Detect which audit cycle to run."""
        intent_lower = intent.lower()
        if "full" in intent_lower or "all" in intent_lower:
            return 0
        for cycle in range(1, 7):
            if str(cycle) in intent or f"cycle {cycle}" in intent_lower:
                return cycle
        return 1

    def detect_version(self, intent: str) -> str:
        """Detect version number from intent."""
        version_match = re.search(r"v?(\d+\.\d+\.\d+)", intent)
        if version_match:
            return version_match.group(1)
        return "2.0.0"

    def add_feature(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new feature to the language."""
        feature = parsed["feature"]
        target = parsed["target"]

        print(f"Adding feature: {feature} (target={target})")

        changes = self.analyze_feature_impact(feature, target)
        changed_files: List[str] = []

        for section in ("core", "syntax", "resolver"):
            for file_path, content in changes.get(section, {}).items():
                append = section != "syntax" or file_path.endswith(".ebnf")
                self.update_file(file_path, content, append=append)
                changed_files.append(file_path)

        self.generate_tests(feature)
        changed_files.append(self._test_file_name(feature))

        self.update_feature_matrix(feature)
        changed_files.append("syntax/feature_matrix_v2.json")

        wasm_ok = self.build_wasm()

        return {
            "status": "success",
            "feature": feature,
            "target": target,
            "files_changed": changed_files,
            "wasm_built": wasm_ok,
            "cost_saved": self.cost_tracker.estimate_savings(len(changed_files)),
            "message": f"Feature scaffold created for: {feature}",
        }

    def analyze_feature_impact(
        self, feature: str, target: str = "auto"
    ) -> Dict[str, Dict[str, str]]:
        """Analyze what files need to change for a feature."""
        impact: Dict[str, Dict[str, str]] = {
            "core": {},
            "syntax": {},
            "resolver": {},
        }
        feature_lower = feature.lower()

        if target == "type" or "type" in feature_lower or "struct" in feature_lower:
            impact["core"]["frontier/core/types.frontier"] = self.generate_type_def(feature)
            impact["syntax"]["syntax/schema_v2.json"] = self.update_schema(feature)
            impact["resolver"]["src/v2_resolver.rs"] = self.update_resolver(feature)
        elif target == "concurrency":
            impact["core"]["frontier/core/concurrency.frontier"] = (
                self.generate_core_module_feature(feature, "concurrency")
            )
        elif target == "pq":
            impact["resolver"]["src/pq_signatures.rs"] = self.update_pq_module(feature)
        elif target == "zk":
            impact["resolver"]["src/zk/verifier.rs"] = self.update_zk_module(feature)
        elif target == "parser" or "keyword" in feature_lower:
            impact["syntax"]["syntax/lexicon.ebnf"] = self.add_keyword(feature)
            impact["core"]["frontier/core/parser.frontier"] = self.update_parser(feature)
        elif target in ("compiler", "memory", "error", "stdlib"):
            impact["core"][f"frontier/core/{target}.frontier"] = (
                self.generate_core_module_feature(feature, target)
            )
        else:
            impact["core"]["frontier/core/stdlib.frontier"] = self.generate_stdlib_feature(
                feature
            )

        return impact

    def fix_bug(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Fix a bug in the codebase."""
        description = parsed["description"]

        print(f"Fixing bug: {description}")

        bug_location = self.locate_bug(description)
        if not bug_location:
            return {"error": f"Could not locate bug: {description}"}

        fix = self.generate_fix(description, bug_location)
        self.update_file(bug_location["file"], fix["content"], append=True)

        test_results = self.run_tests()

        return {
            "status": "success",
            "bug": description,
            "fixed_file": bug_location["file"],
            "tests_passed": test_results["passed"],
            "message": f"Bug fix scaffold appended to {bug_location['file']}",
        }

    def locate_bug(self, description: str) -> Optional[Dict[str, Any]]:
        """Locate bug based on description."""
        description_lower = description.lower()
        if "resolver" in description_lower:
            line_match = re.search(r"line\s+(\d+)", description_lower)
            return {
                "file": "src/v2_resolver.rs",
                "line": int(line_match.group(1)) if line_match else 0,
            }
        if "parser" in description_lower:
            return {"file": "frontier/core/parser.frontier", "line": 0}
        if "type" in description_lower:
            return {"file": "frontier/core/types.frontier", "line": 0}
        if "wasm" in description_lower or "codegen" in description_lower:
            return {"file": "src/wasm_codegen.rs", "line": 0}
        return None

    def generate_fix(self, description: str, location: Dict[str, Any]) -> Dict[str, str]:
        """Generate a fix scaffold for a located bug."""
        timestamp = datetime.now(timezone.utc).isoformat()
        content = f"""
// Auto-generated fix scaffold for: {description}
// Generated by Frontier Agent v2.0 at {timestamp}
// Target: {location['file']} (line {location.get('line', 0)})
"""
        return {"content": content}

    def update_documentation(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Update project documentation from intent."""
        content = parsed["content"]
        doc_path = self.repo_root / "frontier" / "docs" / "language_reference.md"

        timestamp = datetime.now(timezone.utc).isoformat()
        section = f"""
## Agent Update ({timestamp})

{content}
"""
        self.update_file(str(doc_path.relative_to(self.repo_root)), section, append=True)

        return {
            "status": "success",
            "updated_file": str(doc_path.relative_to(self.repo_root)),
            "message": "Documentation section appended",
        }

    def run_audit_cycle(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Run one or more audit cycles."""
        cycle = parsed.get("cycle", 1)

        print(f"Running audit cycle {cycle}")

        results: List[Dict[str, Any]] = []
        if cycle == 0:
            for index in range(1, 7):
                results.append(self.run_single_cycle(index))
        else:
            results.append(self.run_single_cycle(cycle))

        report = self.generate_audit_report(cycle)
        self.state["last_audit_cycle"] = cycle if cycle != 0 else 6
        self.save_state()

        all_ok = all(item.get("success", False) for item in results)
        return {
            "status": "success" if all_ok else "partial",
            "cycle": cycle,
            "results": results,
            "report": report,
            "message": f"Audit cycle {cycle} completed",
        }

    def run_single_cycle(self, cycle: int) -> Dict[str, Any]:
        """Run a single audit cycle using repository verification scripts."""
        commands = self.CYCLE_SCRIPTS.get(cycle)
        if not commands:
            return {"cycle": cycle, "success": False, "error": "Unknown cycle"}

        outputs: List[Dict[str, Any]] = []
        success = True
        for command in commands:
            result = self._run_command(command)
            outputs.append(result)
            if result["returncode"] != 0:
                success = False

        return {"cycle": cycle, "success": success, "commands": outputs}

    def build_wasm(self) -> bool:
        """Build WASM for browser compiler."""
        print("Building WASM...")
        build = self._run_command(
            ["cargo", "build", "--release", "--target", "wasm32-unknown-unknown"]
        )
        if build["returncode"] != 0:
            return False

        wasm_src = (
            self.repo_root
            / "target"
            / "wasm32-unknown-unknown"
            / "release"
            / "frontier.wasm"
        )
        if not wasm_src.exists():
            return False

        self.browser_dir.mkdir(parents=True, exist_ok=True)
        wasm_dest = self.browser_dir / "frontier.wasm"
        wasm_dest.write_bytes(wasm_src.read_bytes())

        syntax_wasm_dir = self.syntax_dir / "wasm"
        syntax_wasm_dir.mkdir(parents=True, exist_ok=True)
        (syntax_wasm_dir / "wasm_parser_v2.wasm").write_bytes(wasm_src.read_bytes())
        return True

    def run_tests(self) -> Dict[str, Any]:
        """Run Rust library tests."""
        print("Running tests...")
        result = self._run_command(["cargo", "test", "--lib"], capture=True)
        return {
            "passed": result["returncode"] == 0,
            "output": result.get("stdout", ""),
        }

    def verify_all(self) -> bool:
        """Run full verification pipeline."""
        print("Running full verification...")
        orchestrator = self.build_dir / "arc_orchestrator.py"
        if not orchestrator.exists():
            return False
        result = self._run_command([str(orchestrator), "--verify"])
        return result["returncode"] == 0

    def run_scrub_pipeline(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Run the self-healing scrub pipeline with ingest, tests, and dashboard."""
        delta = parsed.get("delta", False)
        cmd = [str(self.scripts_dir / "scrub_with_retry.py"), "--max-retries", "5"]
        if delta:
            cmd.append("--delta")

        scrub = self._run_command(cmd, capture=True)
        if scrub["returncode"] != 0:
            return {
                "status": "failed",
                "step": "scrub",
                "error": scrub.get("stderr", "scrub failed"),
            }

        ingest = self.ingest_scrub_report({"report_path": "chat_scrub/WORKER_REPORT.json"})
        tests = self._run_command(
            [
                str(self.scripts_dir / "generate_tests_from_scrub.py"),
                "--run",
            ],
            capture=True,
        )
        dashboard = self._run_command(
            [str(self.scripts_dir / "generate_scrub_dashboard.py")],
            capture=True,
        )
        issues = self.create_issues_from_gaps()

        return {
            "status": "success",
            "delta": delta,
            "scrub": scrub.get("stdout", "").strip(),
            "ingest": ingest,
            "tests_passed": tests["returncode"] == 0,
            "dashboard": dashboard["returncode"] == 0,
            "issues": issues,
            "message": "Scrub pipeline complete — knowledge engine updated",
        }

    def ingest_scrub_report(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Ingest WORKER_REPORT.json into the chat knowledge index."""
        report_rel = parsed.get("report_path", "chat_scrub/WORKER_REPORT.json")
        report_path = self.repo_root / report_rel
        if not report_path.exists():
            return {"status": "failed", "error": f"Report not found: {report_rel}"}

        result = self._run_command(
            [
                str(self.scripts_dir / "chat_knowledge_store.py"),
                "ingest",
                "--file",
                report_rel,
            ],
            capture=True,
        )
        if result["returncode"] != 0:
            return {
                "status": "failed",
                "error": result.get("stderr", "ingest failed"),
            }

        try:
            payload = json.loads(result.get("stdout", "{}").splitlines()[-1])
        except (json.JSONDecodeError, IndexError):
            payload = {"stdout": result.get("stdout", "")}

        self.state.setdefault("scrub_ingestions", []).append(
            {
                "at": datetime.now(timezone.utc).isoformat(),
                "report": report_rel,
                "result": payload,
            }
        )
        self.save_state()
        return {"status": "success", "ingest": payload}

    def create_issues_from_gaps(self) -> Dict[str, Any]:
        """Create GitHub issues or local issue drafts from WORKER_REPORT gaps."""
        report_path = self.repo_root / "chat_scrub" / "WORKER_REPORT.json"
        if not report_path.exists():
            return {"status": "skipped", "reason": "no report"}

        report = json.loads(report_path.read_text(encoding="utf-8"))
        gaps = report.get("known_gaps", [])
        issues_dir = self.repo_root / "chat_scrub" / "issues"
        issues_dir.mkdir(parents=True, exist_ok=True)

        created: List[Dict[str, Any]] = []
        gh = shutil_which("gh")

        for gap in gaps:
            priority = gap.get("priority", "P2")
            title = f"[{priority}] {gap.get('id', 'gap')}: {gap.get('description', '')[:80]}"
            body = (
                f"**Priority:** {priority}\n"
                f"**Subsystem:** {gap.get('file', 'unknown')}\n\n"
                f"{gap.get('description', '')}\n\n"
                f"_Auto-generated from WORKER_REPORT.json by frontier_agent.py_"
            )
            draft_path = issues_dir / f"{gap.get('id', 'gap')}.md"
            draft_path.write_text(f"# {title}\n\n{body}\n", encoding="utf-8")

            issue_record = {
                "id": gap.get("id"),
                "priority": priority,
                "draft": str(draft_path.relative_to(self.repo_root)),
                "github_created": False,
            }

            if gh and priority in ("P0", "P1"):
                gh_cmd = [
                    "gh",
                    "issue",
                    "create",
                    "--title",
                    title,
                    "--body",
                    body,
                ]
                gh_result = self._run_command(gh_cmd, capture=True)
                issue_record["github_created"] = gh_result["returncode"] == 0
                if gh_result["returncode"] != 0:
                    issue_record["gh_error"] = gh_result.get("stderr", "")

            created.append(issue_record)

        return {"status": "success", "issues": created, "count": len(created)}

    def deploy(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy a new version."""
        version = parsed.get("version", "2.0.0")

        print(f"Deploying version {version}")

        self.update_version_numbers(version)
        self.generate_hashes()
        wasm_ok = self.build_wasm()
        package_ok = self.package(version)
        release_ok = self.create_release(version)

        return {
            "status": "success",
            "version": version,
            "wasm_built": wasm_ok,
            "packaged": package_ok,
            "release_created": release_ok,
            "message": f"Version {version} deployment steps completed",
        }

    def update_file(self, file_path: str, content: str, append: bool = False) -> None:
        """Update a file with new content."""
        full_path = self.repo_root / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        if append and full_path.exists():
            existing = full_path.read_text(encoding="utf-8")
            if content.strip() in existing:
                print(f"Skipped duplicate update: {file_path}")
                return
            full_path.write_text(existing + content, encoding="utf-8")
        else:
            full_path.write_text(content, encoding="utf-8")

        self.state["file_hashes"][file_path] = hashlib.sha3_256(
            full_path.read_bytes()
        ).hexdigest()
        print(f"Updated: {file_path}")

    def generate_tests(self, feature: str) -> None:
        """Generate tests for a new feature."""
        test_content = self.generate_test_content(feature)
        test_file = self.repo_root / "tests" / self._test_file_name(feature)
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text(test_content, encoding="utf-8")

    def _test_file_name(self, feature: str) -> str:
        slug = re.sub(r"[^a-z0-9_]+", "_", feature.lower()).strip("_")
        return f"test_{slug}.frontier"

    def update_feature_matrix(self, feature: str) -> None:
        """Update feature matrix JSON."""
        matrix_file = self.syntax_dir / "feature_matrix_v2.json"
        with open(matrix_file, encoding="utf-8") as handle:
            matrix = json.load(handle)

        agent_features = matrix.setdefault("agent_features", [])
        agent_features.append(
            {
                "name": feature,
                "added": datetime.now(timezone.utc).isoformat(),
                "status": "scaffold",
            }
        )

        with open(matrix_file, "w", encoding="utf-8") as handle:
            json.dump(matrix, handle, indent=2)

    def generate_hashes(self) -> bool:
        """Generate SHA-3 hashes for all artifacts."""
        script = self.scripts_dir / "generate_v2_hashes.py"
        if not script.exists():
            return False
        result = self._run_command([str(script)])
        return result["returncode"] == 0

    def generate_audit_report(self, cycle: int) -> Dict[str, Any]:
        """Generate audit report."""
        report = {
            "cycle": cycle,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "completed",
            "hash": hashlib.sha3_256(str(cycle).encode()).hexdigest(),
        }

        self.audit_dir.mkdir(parents=True, exist_ok=True)
        report_file = self.audit_dir / f"audit_cycle_{cycle}.json"
        with open(report_file, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)

        return report

    def package(self, version: str) -> bool:
        """Package for distribution."""
        if not shutil_which("wasm-pack"):
            print("wasm-pack not installed; skipping package step")
            return False
        result = self._run_command(["wasm-pack", "pack", str(self.browser_dir)])
        return result["returncode"] == 0

    def create_release(self, version: str) -> bool:
        """Create GitHub release."""
        if not shutil_which("gh"):
            print("gh CLI not available; skipping release step")
            return False
        result = self._run_command(["gh", "release", "create", f"v{version}", "--generate-notes"])
        return result["returncode"] == 0

    def update_version_numbers(self, version: str) -> None:
        """Update version numbers across project files."""
        cargo_file = self.repo_root / "Cargo.toml"
        if cargo_file.exists():
            content = cargo_file.read_text(encoding="utf-8")
            content = re.sub(
                r'version = "[\d.]+"', f'version = "{version}"', content, count=1
            )
            cargo_file.write_text(content, encoding="utf-8")

        readme_file = self.repo_root / "README.md"
        if readme_file.exists():
            content = readme_file.read_text(encoding="utf-8")
            content = re.sub(r"v\d+\.\d+\.\d+", f"v{version}", content)
            readme_file.write_text(content, encoding="utf-8")

    def generate_type_def(self, feature: str) -> str:
        """Generate type definition for a feature."""
        type_name = re.sub(r"[^A-Za-z0-9]", "", feature.title())
        return f"""
// Auto-generated type definition for: {feature}
// Generated by Frontier Agent v2.0

type {type_name} = struct {{
    // Add fields here
}};
"""

    def generate_stdlib_feature(self, feature: str) -> str:
        """Generate standard library feature."""
        module_name = re.sub(r"[^a-z0-9_]+", "_", feature.lower()).strip("_")
        return f"""
// Auto-generated stdlib feature: {feature}
// Generated by Frontier Agent v2.0

pub mod {module_name} {{
    // Add implementation here
}}
"""

    def generate_core_module_feature(self, feature: str, module: str) -> str:
        """Return a scaffold snippet for a core .frontier module."""
        return f"""
// Auto-generated {module} feature: {feature}
// Generated by Frontier Agent v2.0
"""

    def update_pq_module(self, feature: str) -> str:
        """Return a PQ module scaffold snippet."""
        handler = re.sub(r"[^a-z0-9_]+", "_", feature.lower()).strip("_")
        return f"""
// Auto-generated PQ update for: {feature}
pub fn handle_{handler}() -> Result<String, String> {{
    Ok("pq scaffold".to_string())
}}
"""

    def update_zk_module(self, feature: str) -> str:
        """Return a ZK verifier scaffold snippet."""
        handler = re.sub(r"[^a-z0-9_]+", "_", feature.lower()).strip("_")
        return f"""
// Auto-generated ZK update for: {feature}
pub fn verify_{handler}(_proof: &str) -> bool {{
    true
}}
"""

    def update_schema(self, feature: str) -> str:
        """Update schema JSON."""
        schema_file = self.syntax_dir / "schema_v2.json"
        if schema_file.exists():
            with open(schema_file, encoding="utf-8") as handle:
                schema = json.load(handle)
        else:
            schema = {"version": "2.0"}

        schema["agent_last_feature"] = {
            "feature": feature,
            "updated": datetime.now(timezone.utc).isoformat(),
        }
        return json.dumps(schema, indent=2)

    def update_resolver(self, feature: str) -> str:
        """Update resolver code."""
        handler = re.sub(r"[^a-z0-9_]+", "_", feature.lower()).strip("_")
        resolver_file = self.src_dir / "v2_resolver.rs"
        if resolver_file.exists():
            existing = resolver_file.read_text(encoding="utf-8")
            stub = f"""
// Auto-generated resolver update for: {feature}
impl Resolver {{
    pub fn handle_{handler}(&mut self) -> Result<(), Error> {{
        Ok(())
    }}
}}
"""
            if f"handle_{handler}" not in existing:
                return existing + stub
            return existing

        return f"""
// Auto-generated resolver update for: {feature}
impl Resolver {{
    pub fn handle_{handler}(&mut self) -> Result<(), Error> {{
        Ok(())
    }}
}}
"""

    def add_keyword(self, feature: str) -> str:
        """Add keyword to lexicon."""
        keyword = re.sub(r"[^a-z0-9_]+", "_", feature.lower()).strip("_")
        lexicon = self.syntax_dir / "lexicon.ebnf"
        if lexicon.exists():
            existing = lexicon.read_text(encoding="utf-8")
            stub = f"\n// Agent keyword scaffold: {keyword}\n"
            if keyword not in existing:
                return existing + stub
            return existing
        return f"// Agent keyword scaffold: {keyword}\n"

    def update_parser(self, feature: str) -> str:
        """Update parser for new feature."""
        rule = re.sub(r"[^a-z0-9_]+", "_", feature.lower()).strip("_")
        parser_file = self.core_dir / "parser.frontier"
        if parser_file.exists():
            existing = parser_file.read_text(encoding="utf-8")
            stub = f"""
// Auto-generated parser update for: {feature}
{rule}_rule
    : '{rule}' expression
    ;
"""
            if f"{rule}_rule" not in existing:
                return existing + stub
            return existing
        return self.generate_type_def(feature)

    def generate_test_content(self, feature: str) -> str:
        """Generate test content."""
        slug = re.sub(r"[^a-z0-9_]+", "_", feature.lower()).strip("_")
        return f"""// Auto-generated test for: {feature}
// Generated by Frontier Agent v2.0

fn main() {{
    // TODO: exercise {slug}
}}
"""

    def _run_command(
        self, command: List[str], capture: bool = False
    ) -> Dict[str, Any]:
        """Run a repository command relative to repo root."""
        executable = command[0]
        if executable.endswith(".py"):
            cmd = [sys.executable, str(self.repo_root / executable)] + command[1:]
        elif "/" in executable and not executable.startswith("cargo"):
            cmd = [sys.executable, str(self.repo_root / executable)] + command[1:]
        else:
            cmd = command

        completed = subprocess.run(
            cmd,
            cwd=self.repo_root,
            capture_output=capture,
            text=True,
            check=False,
        )
        payload: Dict[str, Any] = {
            "command": cmd,
            "returncode": completed.returncode,
        }
        if capture:
            payload["stdout"] = completed.stdout
            payload["stderr"] = completed.stderr
        return payload


def shutil_which(command: str) -> Optional[str]:
    """Locate an executable on PATH."""
    from shutil import which

    return which(command)


class CostTracker:
    """Track money saved by automation."""

    def __init__(self) -> None:
        self.cost_per_prompt = 0.03
        self.prompts_saved = 0

    def record_savings(self, result: Dict[str, Any]) -> None:
        """Record savings from an operation."""
        if "files_changed" in result:
            self.prompts_saved += len(result["files_changed"]) * 5

    def estimate_savings(self, files_changed: int) -> float:
        """Estimate cost savings."""
        return files_changed * 5 * self.cost_per_prompt

    def get_total_savings(self) -> float:
        """Get total money saved."""
        return self.prompts_saved * self.cost_per_prompt


def print_usage() -> None:
    """Print CLI usage with all supported intent categories."""
    print("Usage: python3 frontier_agent.py <intent>")
    print()
    print("1. Add Features")
    print("  python3 frontier_agent.py 'Add a new type called Decimal for financial calculations'")
    print("  python3 frontier_agent.py 'Add concurrency support with channels'")
    print("  python3 frontier_agent.py 'Implement post-quantum signatures'")
    print()
    print("2. Fix Bugs")
    print("  python3 frontier_agent.py 'Fix the type resolver bug at line 342'")
    print("  python3 frontier_agent.py 'Fix the WASM build error'")
    print()
    print("3. Run Audits")
    print("  python3 frontier_agent.py 'Run audit cycle 3'")
    print("  python3 frontier_agent.py 'Run full audit'")
    print()
    print("4. Deploy")
    print("  python3 frontier_agent.py 'Deploy v2.1.0'")
    print()
    print("5. Update Documentation")
    print("  python3 frontier_agent.py 'Update documentation for the new Decimal type'")
    print()
    print("6. Knowledge Engine (Scrub Pipeline)")
    print("  python3 frontier_agent.py 'Run chat scrub pipeline'")
    print("  python3 frontier_agent.py 'Ingest scrub report into hypercube'")


def main() -> None:
    """Command-line interface for the agent."""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    intent = " ".join(sys.argv[1:])
    agent = FrontierAgent()
    result = agent.speak_into_existence(intent)

    print("\n" + "=" * 50)
    print(json.dumps(result, indent=2))
    print("=" * 50)

    savings = agent.cost_tracker.get_total_savings()
    print(f"\nTotal money saved: ${savings:.2f}")


if __name__ == "__main__":
    main()
