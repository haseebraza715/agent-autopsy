"""Tests for MCP service-layer functions."""

from __future__ import annotations

import json
from pathlib import Path

from agent_autopsy.mcp import service

SAMPLE_TRACES_DIR = Path(__file__).parent / "sample_traces"


def test_resolve_trace_from_inline_json():
    trace, source, detected_format = service.resolve_trace(
        trace_json={
            "run_id": "inline-1",
            "status": "success",
            "events": [{"type": "message", "content": "hello"}],
        }
    )
    assert trace.run_id == "inline-1"
    assert source == "inline_json"
    assert detected_format == "generic"


def test_detect_patterns_returns_structured_payload():
    result = service.detect_patterns(
        trace_json={
            "run_id": "loop-1",
            "status": "failed",
            "tools": ["search"],
            "events": [
                {"type": "tool", "name": "search", "input": {"q": "x"}, "output": {"ok": 1}},
                {"type": "tool", "name": "search", "input": {"q": "x"}, "output": {"ok": 1}},
                {"type": "tool", "name": "search", "input": {"q": "x"}, "output": {"ok": 1}},
            ],
        }
    )
    assert result["run_id"] == "loop-1"
    assert result["count"] >= 1
    assert any(p["type"] == "infinite_loop" for p in result["patterns"])


def test_validate_trace_reports_valid_sample():
    trace_path = SAMPLE_TRACES_DIR / "successful_run.json"
    result = service.validate_trace(trace_file=str(trace_path))
    assert result["valid"] is True
    assert result["event_count"] > 0


def test_compare_traces_reports_metric_deltas():
    trace_a = SAMPLE_TRACES_DIR / "successful_run.json"
    trace_b = SAMPLE_TRACES_DIR / "loop_failure.json"
    result = service.compare_traces(trace_file_a=str(trace_a), trace_file_b=str(trace_b))
    assert "metric_delta" in result
    assert "pattern_delta" in result
    assert result["trace_a"]["run_id"] != ""
    assert result["trace_b"]["run_id"] != ""


def test_list_traces_with_filters(tmp_path: Path):
    trace_1 = {
        "run_id": "run-success",
        "status": "success",
        "timestamp_start": "2026-01-01T12:00:00Z",
        "events": [],
    }
    trace_2 = {
        "run_id": "run-failed",
        "status": "failed",
        "timestamp_start": "2026-01-02T12:00:00Z",
        "events": [],
    }
    (tmp_path / "a.json").write_text(json.dumps(trace_1))
    (tmp_path / "b.json").write_text(json.dumps(trace_2))

    result = service.list_traces(
        directory=str(tmp_path),
        status="failed",
        date_from="2026-01-02",
        limit=10,
    )
    assert result["count"] == 1
    assert result["traces"][0]["run_id"] == "run-failed"


def test_analyze_trace_and_health_check_deterministic():
    trace_payload = {
        "run_id": "health-1",
        "status": "failed",
        "tools": ["search"],
        "events": [
            {"type": "tool", "name": "search", "input": {"q": "x"}, "output": ""},
            {"type": "error", "error": "timeout"},
        ],
    }
    analysis = service.analyze_trace(trace_json=trace_payload, deterministic_only=True)
    health = service.health_check(trace_json=trace_payload)

    assert analysis["analysis_mode"] == "deterministic"
    assert analysis["run_id"] == "health-1"
    assert "report" in analysis
    assert isinstance(health["health_score"], int)


def test_benchmark_runs_for_directory(tmp_path: Path):
    trace_1 = {
        "run_id": "bench-ok",
        "status": "success",
        "events": [{"type": "message", "content": "ok"}],
    }
    trace_2 = {
        "run_id": "bench-fail",
        "status": "failed",
        "events": [{"type": "error", "error": "boom"}],
    }
    (tmp_path / "a.json").write_text(json.dumps(trace_1))
    (tmp_path / "b.json").write_text(json.dumps(trace_2))

    result = service.benchmark_runs(directory=str(tmp_path), limit=10)

    assert result["total_runs"] == 2
    assert 0.0 <= result["success_rate"] <= 1.0


def test_conversation_flow_tracks_agents_and_handoffs():
    flow = service.conversation_flow(
        trace_json={
            "run_id": "flow-1",
            "status": "failed",
            "events": [
                {"type": "message", "agent_id": "planner", "content": "plan"},
                {"type": "tool", "agent_id": "planner", "name": "search", "input": {"q": "budget"}},
                {"type": "error", "agent_id": "executor", "error": "invalid state"},
            ],
        }
    )

    assert flow["agents"] == ["executor", "planner"]
    assert flow["handoff_count"] == 1
    assert flow["flow_edges"][0]["from_agent"] == "planner"
    assert flow["flow_edges"][0]["to_agent"] == "executor"


def test_monitor_traces_returns_alerts(tmp_path: Path):
    trace = {
        "run_id": "mon-1",
        "status": "failed",
        "tools": ["search"],
        "events": [
            {"type": "tool", "name": "search", "input": {"q": "x"}, "output": {"ok": 1}},
            {"type": "tool", "name": "search", "input": {"q": "x"}, "output": {"ok": 1}},
            {"type": "tool", "name": "search", "input": {"q": "x"}, "output": {"ok": 1}},
        ],
    }
    (tmp_path / "trace.json").write_text(json.dumps(trace))

    result = service.monitor_traces(
        trace_dir=str(tmp_path),
        duration_seconds=0.05,
        poll_interval_seconds=0.01,
        max_alerts=10,
    )

    assert result["alert_count"] >= 1
    assert any(alert["pattern_type"] == "infinite_loop" for alert in result["alerts"])
