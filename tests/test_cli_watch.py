"""
Regression test for `autopsy watch`: a trace that is still being written when
its create event fires must not be dropped permanently — the subsequent
modify event must trigger analysis (once the file is valid).
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

TRACE = {
    "run_id": "watch-race-regression",
    "status": "failed",
    "tools": ["search"],
    "events": [
        {"type": "tool", "name": "search", "input": {"q": "x"}, "output": {"ok": 1}},
        {"type": "tool", "name": "search", "input": {"q": "x"}, "output": {"ok": 1}},
        {"type": "tool", "name": "search", "input": {"q": "x"}, "output": {"ok": 1}},
    ],
}


def test_watch_does_not_drop_trace_written_after_create(tmp_path: Path) -> None:
    target = tmp_path / "run.json"

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "agent_autopsy.cli",
            "watch",
            str(tmp_path),
            "--pattern",
            "*.json",
        ],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        time.sleep(2.0)  # let the watchdog observer start

        # Simulate a trace that is created first and populated in-place after.
        target.write_text('{"run_id": "watch', encoding="utf-8")
        time.sleep(1.0)
        target.write_text(json.dumps(TRACE), encoding="utf-8")
        time.sleep(1.0)

        proc.terminate()
        stdout, stderr = proc.communicate(timeout=15)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.communicate(timeout=15)

    assert "watch-race-regression" in stdout, (
        f"trace completed after its create event was never analyzed:\nstdout={stdout}\nstderr={stderr}"
    )
