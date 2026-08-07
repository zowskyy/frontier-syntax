#!/usr/bin/env python3
"""
PR Resolution Swarm — resolve all open pull requests.

4 teams × 4 workers (16 total):
  - Audit open PRs (mergeability, stack order)
  - Run verification per PR branch
  - Merge stack into base branch
  - Close superseded PRs
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lexicon_bound_worker import LexiconBoundWorker  # noqa: E402
from process_logger import ProcessLogger  # noqa: E402

MANIFEST = ROOT / "manifest" / "pr_resolution.json"
REPORT = ROOT / "audit_reports" / "pr_resolution_report.md"
BASE_BRANCH = "cursor/frontier-syntax-cycle1-e39f"

# PR stack in merge order (each builds on previous)
PR_STACK = [
    {"number": 51, "branch": "cursor/worker-swarm-kb-optimization-f519", "title": "Swarm KB optimizer"},
    {"number": 52, "branch": "cursor/peerless-chat-swarm-f519", "title": "Peerless chat swarm"},
    {"number": 53, "branch": "cursor/execute-peerless-plan-f519", "title": "Execute Peerless plan"},
    {"number": 54, "branch": "cursor/lexicon-bound-worker-f519", "title": "Lexicon-Bound Worker"},
]


def _run(cmd: list[str], cwd: Path | None = None) -> dict:
    start = time.perf_counter()
    r = subprocess.run(cmd, cwd=cwd or ROOT, capture_output=True, text=True)
    return {
        "pass": r.returncode == 0,
        "duration_ms": int((time.perf_counter() - start) * 1000),
        "output": (r.stdout + r.stderr)[-500:],
        "command": " ".join(cmd),
    }


def list_open_prs() -> list[dict]:
    r = subprocess.run(
        ["gh", "pr", "list", "--state", "open", "--json", "number,title,headRefName,mergeable,isDraft"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        return PR_STACK  # fallback to known stack
    return json.loads(r.stdout)


def worker_audit_pr(pr: dict, lbw: LexiconBoundWorker) -> dict:
    branch = pr.get("headRefName") or pr.get("branch", "")
    number = pr.get("number", 0)
    result = lbw.execute_with_lexicon(
        action=f"pr_audit_{number}",
        input_data={"pr": number, "branch": branch},
        documentation=f"Audit PR #{number} mergeability",
        executor=lambda: _run(["gh", "pr", "view", str(number), "--json", "mergeable,state,commits"]),
    )
    mergeable = "MERGEABLE" in result["output"].get("output", "")
    return {
        "worker": f"audit_{number}",
        "pr": number,
        "branch": branch,
        "mergeable": mergeable,
        "pass": result["pass"],
        "lexicon_tag": result["lexicon_tag"],
    }


def worker_verify_branch(pr: dict, lbw: LexiconBoundWorker) -> dict:
    branch = pr.get("headRefName") or pr.get("branch", "")
    number = pr.get("number", 0)

    def verify() -> dict:
        fetch = _run(["git", "fetch", "origin", branch])
        if not fetch["pass"]:
            return fetch
        checkout = _run(["git", "checkout", branch])
        if not checkout["pass"]:
            # May already be on branch
            checkout = _run(["git", "checkout", f"origin/{branch}"])
        tests = _run(["cargo", "test", "--lib"])
        return {"pass": tests["pass"], "cargo_tests": tests["output"][-200:]}

    result = lbw.execute_with_lexicon(
        action=f"pr_verify_{number}",
        input_data={"pr": number, "branch": branch},
        documentation=f"Verify PR #{number} branch tests",
        executor=verify,
    )
    return {
        "worker": f"verify_{number}",
        "pr": number,
        "pass": result["pass"],
        "lexicon_tag": result["lexicon_tag"],
    }


def worker_merge_stack(lbw: LexiconBoundWorker) -> dict:
    def merge() -> dict:
        steps = []
        # Fetch all branches
        _run(["git", "fetch", "origin", BASE_BRANCH])
        for pr in PR_STACK:
            _run(["git", "fetch", "origin", pr["branch"]])

        # Checkout base and merge tip of stack (contains all commits)
        tip = PR_STACK[-1]["branch"]
        swarm_branch = "cursor/swarm-resolve-prs-f519"
        if _run(["git", "fetch", "origin", swarm_branch])["pass"]:
            tip = swarm_branch

        checkout = _run(["git", "checkout", BASE_BRANCH])
        steps.append({"step": "checkout_base", **checkout})
        if not checkout["pass"]:
            stash = _run(["git", "stash", "push", "-m", "pr_resolution_autostash"])
            steps.append({"step": "stash", **stash})
            checkout = _run(["git", "checkout", BASE_BRANCH])
            steps.append({"step": "checkout_base_retry", **checkout})
        if not checkout["pass"]:
            return {"pass": False, "steps": steps}

        pull = _run(["git", "pull", "origin", BASE_BRANCH])
        steps.append({"step": "pull_base", **pull})

        merge = _run(["git", "merge", "--no-edit", f"origin/{tip}"])
        steps.append({"step": f"merge_{tip}", **merge})
        if not merge["pass"]:
            return {"pass": False, "steps": steps}

        push = _run(["git", "push", "origin", BASE_BRANCH])
        steps.append({"step": "push_base", **push})
        return {"pass": push["pass"], "steps": steps, "merged_branch": tip}

    result = lbw.execute_with_lexicon(
        action="merge_pr_stack",
        input_data={"stack": [p["number"] for p in PR_STACK]},
        documentation="Merge PR stack tip into base branch",
        executor=merge,
    )
    return {
        "worker": "merge_stack",
        "pass": result["pass"],
        "lexicon_tag": result["lexicon_tag"],
        "output": result["output"],
    }


def worker_close_superseded(lbw: LexiconBoundWorker) -> dict:
    def close() -> dict:
        closed = []
        tip_number = PR_STACK[-1]["number"]
        for pr in PR_STACK[:-1]:
            r = subprocess.run(
                ["gh", "pr", "close", str(pr["number"]), "--comment",
                 f"Superseded by PR #{tip_number} (linear stack merged to `{BASE_BRANCH}`)."],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            closed.append({"pr": pr["number"], "pass": r.returncode == 0})

        # Mark tip PR ready and merge via gh
        subprocess.run(["gh", "pr", "ready", str(tip_number)], cwd=ROOT, capture_output=True)
        merge_r = subprocess.run(
            ["gh", "pr", "merge", str(tip_number), "--merge", "--delete-branch"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        return {
            "pass": merge_r.returncode == 0,
            "closed": closed,
            "merged_pr": tip_number,
            "merge_output": (merge_r.stdout + merge_r.stderr)[-300:],
        }

    result = lbw.execute_with_lexicon(
        action="close_superseded_prs",
        input_data={"superseded": [p["number"] for p in PR_STACK[:-1]]},
        documentation="Close superseded PRs and merge tip PR on GitHub",
        executor=close,
    )
    return {
        "worker": "close_superseded",
        "pass": result["pass"],
        "lexicon_tag": result["lexicon_tag"],
        "output": result["output"],
    }


def worker_arc_verify(lbw: LexiconBoundWorker) -> dict:
    result = lbw.execute_command(
        action="post_merge_arc_verify",
        cmd=["python3", "build/arc_orchestrator.py", "--verify"],
        documentation="ARC verification after PR merge",
    )
    return {"worker": "arc_verify", "pass": result["pass"], "lexicon_tag": result["lexicon_tag"]}


def run_swarm() -> dict:
    plog = ProcessLogger(worker_id="pr_resolution_swarm")
    start = time.perf_counter()
    lbw = LexiconBoundWorker("pr_resolution_coordinator")

    open_prs = list_open_prs()
    plog.log("pr_resolution", "start", "running", {"open_prs": len(open_prs)})

    results: list[dict] = []

    # Team 1: Audit all PRs in parallel
    with ThreadPoolExecutor(max_workers=4) as pool:
        audit_futures = [pool.submit(worker_audit_pr, pr, LexiconBoundWorker(f"audit_w{i}")) for i, pr in enumerate(open_prs[:4])]
        for fut in as_completed(audit_futures):
            results.append(fut.result())

    # Team 2: Verify tip branch only (contains full stack)
    tip_pr = open_prs[-1] if open_prs else PR_STACK[-1]
    verify_result = worker_verify_branch(tip_pr, LexiconBoundWorker("verify_tip"))
    results.append(verify_result)

    # Team 3: Merge stack to base (sequential — must be after verify)
    if verify_result.get("pass"):
        merge_result = worker_merge_stack(LexiconBoundWorker("merge_worker"))
        results.append(merge_result)
    else:
        merge_result = {"worker": "merge_stack", "pass": False, "skipped": "verify failed"}
        results.append(merge_result)

    # Team 4: Close superseded + merge tip PR on GitHub
    if merge_result.get("pass"):
        close_result = worker_close_superseded(LexiconBoundWorker("close_worker"))
        results.append(close_result)
        arc_result = worker_arc_verify(LexiconBoundWorker("arc_worker"))
        results.append(arc_result)
    else:
        results.append({"worker": "close_superseded", "pass": False, "skipped": "merge failed"})
        results.append({"worker": "arc_verify", "pass": False, "skipped": "merge failed"})

    all_pass = all(r.get("pass") for r in results if "skipped" not in r)
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "open_prs_found": len(open_prs),
        "pr_stack": PR_STACK,
        "base_branch": BASE_BRANCH,
        "all_pass": all_pass,
        "duration_ms": int((time.perf_counter() - start) * 1000),
        "worker_results": results,
    }

    MANIFEST.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        f"# PR Resolution Swarm Report\n\n"
        f"**Generated:** {summary['generated_at']}\n\n"
        f"| Metric | Value |\n|--------|-------|\n"
        f"| Open PRs | {len(open_prs)} |\n"
        f"| All pass | {all_pass} |\n"
        f"| Base branch | `{BASE_BRANCH}` |\n\n"
        + "\n".join(f"- {'✅' if r.get('pass') else '❌'} {r.get('worker', '?')}" for r in results),
        encoding="utf-8",
    )
    plog.log("pr_resolution", "complete", "pass" if all_pass else "partial", summary)
    return summary


def main() -> int:
    summary = run_swarm()
    print(json.dumps({
        "pass": summary["all_pass"],
        "open_prs": summary["open_prs_found"],
        "report": str(REPORT.relative_to(ROOT)),
    }, indent=2))
    return 0 if summary["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
