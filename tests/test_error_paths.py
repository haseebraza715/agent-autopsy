"""Error-path coverage for parsing and CLI boundaries."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from src.errors import ParseError
from src.ingestion import TraceNormalizer
from src.ingestion.parser import parse_trace_data

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_parse_truncated_json_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text('{"run_id": "x", "events": [', encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "src.cli", "analyze", str(bad), "--no-llm"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 1


def test_parse_trace_data_type_error() -> None:
    with pytest.raises(ParseError, match="dictionary"):
        parse_trace_data([])  # type: ignore[arg-type]


def test_cli_summary_missing_file() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "src.cli", "summary", str(REPO_ROOT / "nonexistent_trace.json")],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode != 0


def test_cli_validate_empty_object() -> None:
    p = REPO_ROOT / "tests" / "fixtures" / "e2e" / "generic.json"
    proc = subprocess.run(
        [sys.executable, "-m", "src.cli", "validate", str(p)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0


def test_malformed_events_rejected_or_validated() -> None:
    """A dict missing required trace shape should still parse generically or surface issues."""
    data = {"run_id": "bad-shape", "status": "success", "events": [{"type": "llm_call"}]}
    trace = parse_trace_data(data)
    issues = TraceNormalizer.validate(trace)
    assert isinstance(issues, list)
