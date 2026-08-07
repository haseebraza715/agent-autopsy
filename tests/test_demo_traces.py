"""
Regression tests for the offline demo assets: examples/traces/loop_failure.json,
examples/traces/loop_fixed.json, and scripts/demo.sh.

Guards the behavior the demo depends on:
- fixed trace is clean (exit 0, no signals, 100/100 health)
- failing trace yields an infinite-loop signal (exit 1, 23/100 health)
- diff reports the loop patterns ONLY in the failing run
- artifacts include the LoopGuard
- diff JSON output is reproducible across processes
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from agent_autopsy.api import load_trace
from agent_autopsy.preanalysis import PatternDetector, PatternType, RootCauseBuilder

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = REPO_ROOT / "examples" / "traces"
FAILING = EXAMPLES / "loop_failure.json"
FIXED = EXAMPLES / "loop_fixed.json"
DEMO = REPO_ROOT / "scripts" / "demo.sh"

pytestmark = pytest.mark.skipif(
    not (FAILING.exists() and FIXED.exists()),
    reason="demo traces missing",
)


def _cli(*args: str, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "agent_autopsy.cli", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=120,
    )


class TestDemoTraces:
    def test_loop_fixed_trace_is_clean(self) -> None:
        trace = load_trace(FIXED)
        assert trace.status.value == "success"
        assert trace.stats.num_errors == 0
        assert PatternDetector(trace).detect_all() == []
        assert RootCauseBuilder(trace).build().signals == []

    def test_loop_failure_trace_has_loop_signal(self) -> None:
        trace = load_trace(FAILING)
        patterns = PatternDetector(trace).detect_all()
        assert any(p.pattern_type == PatternType.INFINITE_LOOP for p in patterns)
        assert any(p.pattern_type == PatternType.ERROR_CASCADE for p in patterns)

    def test_cli_analyze_exit_codes(self) -> None:
        failing = _cli("analyze", str(FAILING), "--no-llm", "--no-embeddings", "-q")
        fixed = _cli("analyze", str(FIXED), "--no-llm", "--no-embeddings", "-q")
        assert failing.returncode == 1, failing.stderr + failing.stdout
        assert fixed.returncode == 0, fixed.stderr + fixed.stdout

    def test_cli_diff_patterns_only_in_failing_run(self) -> None:
        proc = _cli("diff", str(FAILING), str(FIXED), "-f", "json")
        assert proc.returncode == 0, proc.stderr + proc.stdout
        data = json.loads(proc.stdout)
        assert "infinite_loop" in data["patterns_only_in_a"]
        assert "infinite_loop" not in data["patterns_only_in_b"]
        assert data["patterns_only_in_b"] == []

    def test_diff_json_output_is_reproducible_across_processes(self) -> None:
        # Regression: tool signatures used to embed Python's process-salted
        # hash() value, so diff JSON differed on every invocation.
        first = _cli("diff", str(FAILING), str(FIXED), "-f", "json")
        second = _cli("diff", str(FAILING), str(FIXED), "-f", "json")
        assert first.returncode == second.returncode == 0
        assert first.stdout == second.stdout

    def test_artifacts_include_loop_guard(self, tmp_path: Path) -> None:
        out = tmp_path / "artifacts"
        proc = _cli(
            "analyze",
            str(FAILING),
            "--no-llm",
            "--no-embeddings",
            "--artifacts",
            str(out),
            "-q",
        )
        assert proc.returncode == 1  # findings detected
        assert (out / "loop_guard.py").is_file()
        assert (out / "error_handler.py").is_file()
        assert (out / "manifest.json").is_file()
        manifest = json.loads((out / "manifest.json").read_text())
        assert {a["name"] for a in manifest["artifacts"]} >= {"loop_guard.py", "error_handler.py"}


class TestDemoScript:
    def test_demo_script_syntax(self) -> None:
        proc = subprocess.run(
            ["bash", "-n", str(DEMO)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert proc.returncode == 0, proc.stderr

    @pytest.mark.skipif(
        not (REPO_ROOT / ".venv" / "bin" / "autopsy").exists(),
        reason="demo needs an installed CLI in .venv; skip in fresh CI envs",
    )
    def test_demo_runs_end_to_end_offline(self) -> None:
        env = {"AUTOPSY_DEMO_FAST": "1", "AUTOPSY_DEMO_GAP": "0", "PATH": "/usr/bin:/bin:/usr/local/bin"}
        proc = subprocess.run(
            ["bash", str(DEMO)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=600,
            env=env,
        )
        assert proc.returncode == 0, proc.stderr + proc.stdout
        assert "demo complete" in proc.stdout
        # No stray temp dirs left behind by the artifact stage.
        assert list(REPO_ROOT.glob(".demo-fixes.*")) == []
