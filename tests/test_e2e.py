"""End-to-end CLI smoke: parse → pre-analysis → deterministic report for each trace format."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "e2e"


@pytest.mark.parametrize(
    "filename,expected_substring",
    [
        ("generic.json", "e2e-generic"),
        ("langgraph.json", "e2e-langgraph"),
        ("langchain.json", "e2e-langchain"),
        ("opentelemetry.json", "e2e-otel-trace"),
    ],
)
def test_cli_analyze_pipeline_no_llm(filename: str, expected_substring: str) -> None:
    trace_path = FIXTURES / filename
    assert trace_path.exists(), f"missing fixture {trace_path}"

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.cli",
            "analyze",
            str(trace_path),
            "--no-llm",
            "--no-embeddings",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    combined = proc.stdout + proc.stderr
    assert expected_substring in combined
    assert "Pre-Analysis" in combined or "pre-analysis" in combined.lower() or "## Summary" in combined
