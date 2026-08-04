"""Focused demo presentation stays backed by deterministic trace findings."""

from pathlib import Path

from agent_autopsy import api
from agent_autopsy.ui.demo_page import build_demo_diagnosis

FIXTURES = Path(__file__).parent / "fixtures" / "real_traces"


def test_retry_storm_demo_uses_real_trace_evidence() -> None:
    trace = api.load_trace(FIXTURES / "fail_retrystorm_b8f735cd.json")
    preanalysis = api.run_preanalysis(trace)

    diagnosis = build_demo_diagnosis(trace, preanalysis)

    assert diagnosis.category == "Retry Storm"
    assert diagnosis.first_failure_id == 1
    assert diagnosis.causal_event_ids == tuple(range(1, 9))
    assert "health_check" in diagnosis.detail
    assert "8 times" in diagnosis.detail
    assert len(diagnosis.fixes) == 3


def test_non_retry_sample_uses_primary_analyzer_signal() -> None:
    trace = api.load_trace(FIXTURES / "test_hallucination_6b5f8c42.json")
    preanalysis = api.run_preanalysis(trace)

    diagnosis = build_demo_diagnosis(trace, preanalysis)

    assert diagnosis.category == "Hallucinated Tool"
    assert diagnosis.causal_event_ids
    assert diagnosis.cause
    assert diagnosis.fixes
