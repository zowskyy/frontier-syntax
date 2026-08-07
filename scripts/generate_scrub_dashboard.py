#!/usr/bin/env python3
"""Generate live HTML metrics dashboard for chat scrub."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
METRICS = ROOT / "chat_scrub" / "metrics.json"
DECISION_LOG = ROOT / "chat_scrub" / "decision_log.jsonl"
WORKER_REPORT = ROOT / "chat_scrub" / "WORKER_REPORT.json"
OUTPUT = ROOT / "chat_scrub" / "dashboard.html"


def load_decision_confidence() -> list[float]:
    if not DECISION_LOG.exists():
        return []
    confidences = []
    for line in DECISION_LOG.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        confidences.append(float(entry.get("confidence", 0)))
    return confidences


def main() -> int:
    history = []
    if METRICS.exists():
        history = json.loads(METRICS.read_text(encoding="utf-8")).get("history", [])

    report = {}
    if WORKER_REPORT.exists():
        report = json.loads(WORKER_REPORT.read_text(encoding="utf-8"))

    confidences = load_decision_confidence()
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    low_conf = sum(1 for c in confidences if c < 0.95)

    gaps = report.get("known_gaps", [])
    closed = sum(1 for g in gaps if g.get("status") == "closed")
    gap_rate = (closed / len(gaps) * 100) if gaps else 0.0

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    rows = "".join(
        f"<tr><td>{h.get('at', '')}</td><td>{h.get('new_entries', 0)}</td>"
        f"<td>{h.get('duration_ms', 0)}</td><td>{h.get('status', '')}</td></tr>"
        for h in history[-20:]
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Frontier Chat Scrub Dashboard</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #0d1117; color: #e6edf3; }}
    h1 {{ color: #58a6ff; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }}
    .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 1rem; }}
    .value {{ font-size: 2rem; font-weight: bold; color: #3fb950; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 1.5rem; }}
    th, td {{ border: 1px solid #30363d; padding: 0.5rem; text-align: left; }}
    th {{ background: #21262d; }}
  </style>
</head>
<body>
  <h1>Frontier Chat Scrub — Live Metrics</h1>
  <p>Updated: {now}</p>
  <div class="grid">
    <div class="card"><div>Knowledge Items</div><div class="value">{report.get('code_blocks_extracted', 0)}</div></div>
    <div class="card"><div>Decisions Logged</div><div class="value">{report.get('decisions_logged', 0)}</div></div>
    <div class="card"><div>Avg Confidence</div><div class="value">{avg_conf:.2f}</div></div>
    <div class="card"><div>Low-Conf Reviews</div><div class="value">{low_conf}</div></div>
    <div class="card"><div>Gap Closure Rate</div><div class="value">{gap_rate:.0f}%</div></div>
    <div class="card"><div>Attack Vectors</div><div class="value">{len(report.get('attack_vectors', []))}</div></div>
  </div>
  <h2>Recent Runs</h2>
  <table>
    <tr><th>Time</th><th>New Entries</th><th>Duration (ms)</th><th>Status</th></tr>
    {rows or '<tr><td colspan="4">No runs recorded yet</td></tr>'}
  </table>
</body>
</html>"""

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"✅ Dashboard written to {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
