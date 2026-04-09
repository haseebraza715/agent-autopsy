"""Tests for report generation output quality."""

from datetime import datetime

from src.analysis.agent import AnalysisResult
from src.output import ReportGenerator
from src.schema import (
    Trace,
    TraceEvent,
    TraceStatus,
    EventType,
    EnvironmentInfo,
)


def _trace_with_events() -> Trace:
    trace = Trace(
        run_id="report-test-run",
        timestamp_start=datetime(2026, 1, 1, 0, 0, 0),
        timestamp_end=datetime(2026, 1, 1, 0, 1, 0),
        status=TraceStatus.FAILED,
        env=EnvironmentInfo(agent_framework="test", model="gpt-4"),
        events=[
            TraceEvent(event_id=0, type=EventType.DECISION, name="router", agent_id="planner"),
            TraceEvent(event_id=1, type=EventType.TOOL_CALL, name="search", input={"q": "x"}, output=None, agent_id="executor"),
            TraceEvent(event_id=2, type=EventType.ERROR, name="search", output="timeout"),
        ],
    )
    trace.stats = trace.calculate_stats()
    return trace


class TestReportGenerator:
    """Deterministic report behavior tests."""

    def test_health_score_and_timeline_markers(self):
        trace = _trace_with_events()
        result = AnalysisResult(
            report="",
            trace_summary={"total_events": 3, "errors": 1},
            preanalysis={
                "signals": [
                    {
                        "type": "timeout_pattern",
                        "severity": "high",
                        "evidence": "timeouts repeated",
                        "events": [1, 2],
                    }
                ],
                "top_suspects": [
                    {
                        "hypothesis": "Timeout bottleneck",
                        "confidence": 0.8,
                        "supporting_events": [1, 2],
                        "category": "ops",
                        "suggested_fixes": ["Set strict timeouts"],
                    }
                ],
            },
            success=True,
        )

        report = ReportGenerator(trace, result).generate()

        assert 0 <= report.health_score <= 100
        assert report.health_score < 100
        assert any(line.startswith("[001] !") or line.startswith("[002] X") for line in report.timeline)
        assert any("@planner" in line or "@executor" in line for line in report.timeline)

    def test_pattern_templates_are_added_to_fixes(self):
        trace = _trace_with_events()
        result = AnalysisResult(
            report="",
            trace_summary={"total_events": 3, "errors": 1},
            preanalysis={
                "signals": [
                    {"type": "infinite_loop", "severity": "critical", "events": [1, 2]},
                    {"type": "auth_permission_failure", "severity": "high", "events": [2]},
                ],
                "top_suspects": [],
            },
            success=True,
        )

        report = ReportGenerator(trace, result).generate()

        assert any("max_iterations" in item for item in report.fix_recommendations["code"])
        assert any("401/403" in item for item in report.fix_recommendations["ops"])
