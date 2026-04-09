"""Tests for advanced Phase 5 helpers."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src.advanced import benchmark_traces, compare_traces_advanced, LiveTraceMonitor
from src.schema import EnvironmentInfo, EventType, Trace, TraceEvent, TraceStatus


def _trace(run_id: str, events: list[TraceEvent], status: TraceStatus = TraceStatus.SUCCESS) -> Trace:
    trace = Trace(
        run_id=run_id,
        timestamp_start=datetime(2026, 1, 1, 0, 0, 0),
        timestamp_end=datetime(2026, 1, 1, 0, 1, 0),
        status=status,
        env=EnvironmentInfo(agent_framework="test", model="gpt-4", tools_available=["search", "calc"]),
        events=events,
    )
    trace.stats = trace.calculate_stats()
    return trace


def test_compare_traces_advanced_detects_tool_and_llm_changes():
    trace_a = _trace(
        "a",
        [
            TraceEvent(event_id=0, type=EventType.LLM_CALL, output="initial plan"),
            TraceEvent(event_id=1, type=EventType.TOOL_CALL, name="search", input={"q": "budget"}, output={"ok": 1}),
        ],
    )
    trace_b = _trace(
        "b",
        [
            TraceEvent(event_id=0, type=EventType.LLM_CALL, output="revised plan"),
            TraceEvent(event_id=1, type=EventType.TOOL_CALL, name="search", input={"q": "forecast"}, output={"ok": 1}),
            TraceEvent(event_id=2, type=EventType.TOOL_CALL, name="calc", input={"x": 2}, output={"y": 4}),
        ],
    )

    result = compare_traces_advanced(trace_a, trace_b)

    assert "search" in result.changed_tool_signatures
    assert result.new_tool_signatures
    assert result.removed_tool_signatures
    assert len(result.changed_llm_outputs) == 1


def test_benchmark_traces_reports_aggregates(tmp_path: Path):
    trace_ok = {
        "run_id": "ok-1",
        "status": "success",
        "events": [
            {"type": "llm", "token_count": 100, "output": "ok"},
            {"type": "tool", "name": "search", "output": {"ok": 1}, "latency_ms": 50},
        ],
    }
    trace_bad = {
        "run_id": "bad-1",
        "status": "failed",
        "events": [
            {"type": "tool", "name": "search", "input": {"q": "x"}, "output": {"ok": 1}},
            {"type": "tool", "name": "search", "input": {"q": "x"}, "output": {"ok": 1}},
            {"type": "tool", "name": "search", "input": {"q": "x"}, "output": {"ok": 1}},
            {"type": "error", "error": "boom"},
        ],
    }

    p1 = tmp_path / "ok.json"
    p2 = tmp_path / "bad.json"
    p1.write_text(json.dumps(trace_ok))
    p2.write_text(json.dumps(trace_bad))

    result = benchmark_traces([p1, p2]).to_dict()

    assert result["total_runs"] == 2
    assert result["success_rate"] == 0.5
    assert result["average_errors"] >= 0
    assert isinstance(result["top_failure_patterns"], list)


def test_live_monitor_emits_alerts_for_new_trace(tmp_path: Path):
    trace = {
        "run_id": "monitor-1",
        "status": "failed",
        "tools": ["search"],
        "events": [
            {"type": "tool", "name": "search", "input": {"q": "x"}, "output": {"ok": 1}},
            {"type": "tool", "name": "search", "input": {"q": "x"}, "output": {"ok": 1}},
            {"type": "tool", "name": "search", "input": {"q": "x"}, "output": {"ok": 1}},
        ],
    }
    path = tmp_path / "trace.json"
    path.write_text(json.dumps(trace))

    monitor = LiveTraceMonitor(trace_dir=tmp_path, poll_interval_seconds=0.01)

    alerts_first = monitor.run_once()
    alerts_second = monitor.run_once()

    assert any(alert.pattern_type == "infinite_loop" for alert in alerts_first)
    assert alerts_second == []
