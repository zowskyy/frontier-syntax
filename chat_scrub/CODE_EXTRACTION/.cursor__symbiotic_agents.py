#!/usr/bin/env python3
"""
Frontier Symbiotic Tandem — Master Orchestrator + Worker Agent

Wires the enhanced frontier_agent.py into a parallel execution system with
cross-verification and a feedback loop.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import sys
import uuid
from pathlib import Path
from queue import Empty, Queue
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from frontier_agent import FrontierAgent  # noqa: E402


DEFAULT_INTENTS = [
    "Run audit cycle 1",
    "Update documentation for symbiotic tandem integration",
    "Add a new type called Decimal with precision support",
    "Fix the type resolver bug at line 342",
    "Run audit cycle 3",
]


class MasterOrchestrator:
    """Plans intents, verifies results, and learns from outcomes."""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root
        self.agent = FrontierAgent()
        self.worker_queue: Queue = Queue()
        self.result_queue: Queue = Queue()
        self.verification_log: List[Dict[str, Any]] = []
        self.learning_log: List[Dict[str, Any]] = []

    def plan_repair(self, intents: Optional[List[str]] = None) -> List[Dict[str, str]]:
        """Create repair plan and enqueue natural-language intents."""
        plan = intents or DEFAULT_INTENTS
        tasks: List[Dict[str, str]] = []
        for intent in plan:
            task_id = str(uuid.uuid4())[:8]
            task = {"id": task_id, "intent": intent}
            self.worker_queue.put(task)
            tasks.append(task)
        return tasks

    def verify_intent_result(
        self, intent: str, result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Cross-verify a worker result by re-running in verify mode."""
        verification = self.agent.verify_intent(intent, prior_result=result)
        expected = result.get("status", "failed")
        actual = verification.get("status", "failed")
        ok = actual == expected or (
            expected in ("success", "partial") and actual in ("success", "partial")
        )
        record = {
            "intent": intent,
            "expected": expected,
            "verified": actual,
            "status": "success" if ok else "failed",
            "message": "Verification passed." if ok else (
                f"Verification failed: expected {expected}, got {actual}"
            ),
            "detail": verification,
        }
        self.verification_log.append(record)
        return record

    def learn_from_result(self, intent: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Learn from success/failure and optionally re-queue retries."""
        status = result.get("status", "failed")
        outcome = "success" if status in ("success", "partial") else "failure"
        self.agent.learn(intent, outcome)
        record = {"intent": intent, "outcome": outcome, "status": status}
        self.learning_log.append(record)

        if outcome == "failure" and not result.get("retry"):
            self.worker_queue.put({"id": str(uuid.uuid4())[:8], "intent": intent, "retry": True})
            record["requeued"] = True
        return record

    def collect_results(self, timeout: float = 0.1) -> List[Tuple[str, Dict[str, Any]]]:
        """Drain result queue."""
        results: List[Tuple[str, Dict[str, Any]]] = []
        while True:
            try:
                results.append(self.result_queue.get(timeout=timeout))
            except Empty:
                break
        return results


class WorkerAgent:
    """Executes natural-language intents in parallel via FrontierAgent."""

    def __init__(self, orchestrator: MasterOrchestrator, max_workers: int = 4) -> None:
        self.orchestrator = orchestrator
        self.max_workers = max_workers

    def execute_intent(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute one intent using the enhanced Frontier agent."""
        intent = task["intent"]
        try:
            result = self.orchestrator.agent.process(intent)
            result["task_id"] = task.get("id")
            result["intent"] = intent
            result["retry"] = task.get("retry", False)
            return result
        except Exception as exc:  # noqa: BLE001
            return {
                "status": "failed",
                "intent": intent,
                "task_id": task.get("id"),
                "error": str(exc),
            }

    def run(self) -> List[Dict[str, Any]]:
        """Run worker with parallel intent execution."""
        tasks: List[Dict[str, Any]] = []
        while not self.orchestrator.worker_queue.empty():
            tasks.append(self.orchestrator.worker_queue.get())

        if not tasks:
            return []

        results: List[Dict[str, Any]] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self.execute_intent, task): task for task in tasks
            }
            for future in concurrent.futures.as_completed(futures):
                task = futures[future]
                result = future.result()
                self.orchestrator.result_queue.put((task["id"], result))
                results.append(result)

        return results


class SymbioticTandem:
    """Coordinates Master Orchestrator and Worker Agent."""

    def __init__(self, workspace_root: Path, max_workers: int = 4) -> None:
        self.master = MasterOrchestrator(workspace_root)
        self.worker = WorkerAgent(self.master, max_workers=max_workers)

    def run(self, intents: Optional[List[str]] = None) -> Dict[str, Any]:
        """Plan, execute in parallel, verify, and learn."""
        tasks = self.master.plan_repair(intents)
        worker_results = self.worker.run()

        verifications: List[Dict[str, Any]] = []
        learning: List[Dict[str, Any]] = []
        for result in worker_results:
            intent_str = result.get("intent", "unknown")
            verifications.append(self.master.verify_intent_result(intent_str, result))
            learning.append(self.master.learn_from_result(intent_str, result))

        summary = {
            "tasks_planned": len(tasks),
            "tasks_executed": len(worker_results),
            "verifications": verifications,
            "learning": learning,
            "worker_results": worker_results,
        }
        return summary


def run_canonical_intent_tests() -> Dict[str, Any]:
    """Test all five intent categories directly."""
    agent = FrontierAgent()
    tests = [
        "Add a new type called Decimal with precision support",
        "Fix the type resolver bug at line 342",
        "Run audit cycle 3",
        "Deploy v2.1.0",
        "Update documentation for the new Decimal type",
    ]
    results: Dict[str, Any] = {}
    for intent in tests:
        parsed = agent.parse_intent(intent)
        verify_only = agent.verify_intent(intent)
        results[intent] = {
            "parsed_type": parsed["type"],
            "verify_status": verify_only.get("status"),
        }
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Frontier Symbiotic Tandem")
    parser.add_argument(
        "--test-intents",
        action="store_true",
        help="Test all five intent categories (parse + verify only)",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run symbiotic tandem with safe default intents",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Parallel worker count (default: 4)",
    )
    args = parser.parse_args()

    if args.test_intents:
        results = run_canonical_intent_tests()
        print(json.dumps(results, indent=2))
        return

    tandem = SymbioticTandem(REPO_ROOT, max_workers=args.workers)
    intents = DEFAULT_INTENTS if args.demo else None
    summary = tandem.run(intents)

    print("=" * 60)
    print("SYMBIOTIC TANDEM COMPLETE")
    print("=" * 60)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
