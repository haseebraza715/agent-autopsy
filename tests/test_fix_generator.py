"""Tests for advanced deterministic fix generation."""

from __future__ import annotations

from datetime import datetime

from src.output import FixSuggestionGenerator
from src.preanalysis import RootCauseBuilder
from src.schema import EnvironmentInfo, EventType, Trace, TraceEvent, TraceStatus


def _loop_trace() -> Trace:
    trace = Trace(
        run_id="fix-trace",
        timestamp_start=datetime(2026, 1, 1, 0, 0, 0),
        status=TraceStatus.FAILED,
        env=EnvironmentInfo(agent_framework="test", tools_available=["search"]),
        events=[
            TraceEvent(event_id=0, type=EventType.TOOL_CALL, name="search", input={"q": "x"}, output={"ok": 1}),
            TraceEvent(event_id=1, type=EventType.TOOL_CALL, name="search", input={"q": "x"}, output={"ok": 1}),
            TraceEvent(event_id=2, type=EventType.TOOL_CALL, name="search", input={"q": "x"}, output={"ok": 1}),
            TraceEvent(event_id=3, type=EventType.ERROR, name="search", output="timeout"),
            TraceEvent(event_id=4, type=EventType.ERROR, name="search", output="still failing"),
        ],
    )
    trace.stats = trace.calculate_stats()
    return trace


def test_fix_generator_emits_loop_and_cascade_guidance():
    trace = _loop_trace()
    preanalysis = RootCauseBuilder(trace).build()

    suggestions = FixSuggestionGenerator(trace, preanalysis).to_dict()

    assert suggestions
    titles = {suggestion["title"] for suggestion in suggestions}
    assert "Add max-iteration guard to looping node" in titles
    assert any("error boundary" in title.lower() for title in titles)
