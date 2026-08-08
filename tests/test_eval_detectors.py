"""
Regression tests for the honest detector evaluator and the CLI exit gate.

Guards the hand-labeled negative controls (must_not_include) added to
tests/fixtures/real_traces and the recovered-error exit behavior.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

from agent_autopsy.cli import _trace_has_findings
from agent_autopsy.ingestion import TraceNormalizer, parse_trace_file
from agent_autopsy.preanalysis import PatternDetector
from agent_autopsy.preanalysis.suspects import PreAnalysisBundle
from agent_autopsy.schema import (
    EnvironmentInfo,
    EventError,
    EventType,
    Trace,
    TraceEvent,
    TraceStatus,
)
from agent_autopsy.utils.config import get_config

REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS = REPO_ROOT / "tests" / "fixtures" / "real_traces"

NEGATIVE_CONTROLS = [
    "neg_slow_success_a1b2c3d4.json",
    "neg_repeated_success_e5f6a7b8.json",
    "neg_repeated_query_c9d0e1f2.json",
    "neg_delete_empty_3a5b7c9d.json",
    "neg_timeout_language_4b6d8f0a.json",
]


def test_negative_controls_produce_no_detections() -> None:
    get_config().skip_embeddings = True
    for name in NEGATIVE_CONTROLS:
        trace = TraceNormalizer.normalize(parse_trace_file(CORPUS / name))
        detected = {p.pattern_type.value for p in PatternDetector(trace).detect_all()}
        assert detected == set(), f"{name} produced unexpected detections: {detected}"


def test_positive_controls_for_previously_uncovered_detectors() -> None:
    get_config().skip_embeddings = True
    expected = {
        "pos_retrystorm_7e9a1c3f.json": {"retry_storm"},
        "pos_goaldrift_1f3d5b7a.json": {"goal_drift"},
        "pos_stale_context_2a4c6e8f.json": {"stale_context"},
        "pos_inter_agent_5c7e9a1b.json": {"inter_agent_failure"},
    }
    for name, must in expected.items():
        trace = TraceNormalizer.normalize(parse_trace_file(CORPUS / name))
        detected = {p.pattern_type.value for p in PatternDetector(trace).detect_all()}
        assert must <= detected, f"{name} missing {must - detected}"


def test_eval_script_passes_on_hand_labeled_corpus(tmp_path: Path) -> None:
    out = tmp_path / "detector-eval.json"
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "eval_detectors.py"), "--json-out", str(out)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert out.is_file()


def _build_trace(events, status: TraceStatus, error_summary: str | None = None) -> Trace:
    return Trace(
        run_id="recovered-error-test",
        timestamp_start=datetime(2026, 1, 1),
        timestamp_end=datetime(2026, 1, 1, 0, 0, 5),
        status=status,
        env=EnvironmentInfo(agent_framework="test"),
        events=events,
        error_summary=error_summary,
    )


def test_recovered_error_with_zero_signals_exits_cleanly() -> None:
    events = [
        TraceEvent(
            event_id=0,
            type=EventType.TOOL_CALL,
            name="api",
            output="ok",
            error=EventError(message="retried and recovered"),
        )
    ]
    trace = _build_trace(events, TraceStatus.SUCCESS)
    trace.stats.num_errors = 1
    assert _trace_has_findings(trace, PreAnalysisBundle()) is False


def test_non_success_status_always_exits_with_findings() -> None:
    events = [TraceEvent(event_id=0, type=EventType.MESSAGE, output="done")]
    trace = _build_trace(events, TraceStatus.FAILED, error_summary="boom")
    assert _trace_has_findings(trace, PreAnalysisBundle()) is True


def test_any_signal_exits_with_findings() -> None:
    events = [TraceEvent(event_id=0, type=EventType.MESSAGE, output="done")]
    trace = _build_trace(events, TraceStatus.SUCCESS)
    bundle = PreAnalysisBundle()
    from agent_autopsy.preanalysis.suspects import Signal

    bundle.signals = [Signal(type="infinite_loop", severity="critical", evidence="loop")]
    assert _trace_has_findings(trace, bundle) is True
