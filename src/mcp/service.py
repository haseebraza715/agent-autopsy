"""
Service layer for MCP tools.

This module contains framework-agnostic functions so MCP integration
can stay thin and unit-testable.
"""

from __future__ import annotations

from datetime import date, datetime
import json
from pathlib import Path
from typing import Any

from src.advanced import benchmark_trace_directory, benchmark_traces, compare_traces_advanced, LiveTraceMonitor
from src.analysis import run_analysis
from src.analysis.agent import AnalysisResult, run_analysis_without_llm
from src.ingestion import TraceNormalizer, parse_trace_data, parse_trace_file, TraceParser
from src.output import ReportGenerator, FixSuggestionGenerator
from src.plugins import get_plugin_manager
from src.preanalysis import PatternDetector, PatternType, RootCauseBuilder
from src.schema import Trace, TraceEvent
from src.tracing import get_trace_config
from src.utils.config import get_config


def resolve_trace(
    trace_file: str | None = None,
    trace_json: dict[str, Any] | str | None = None,
) -> tuple[Trace, str, str]:
    """
    Resolve and normalize a trace from file path or raw JSON payload.

    Returns:
        (trace, source, detected_format)
    """
    raw_data: dict[str, Any] | None = None
    source = "inline_json"

    if trace_json is not None:
        if isinstance(trace_json, str):
            raw_data = json.loads(trace_json)
        elif isinstance(trace_json, dict):
            raw_data = trace_json
        else:
            raise TypeError("trace_json must be a dict or JSON string")

        detected_format = TraceParser.detect_format(raw_data)
        trace = parse_trace_data(raw_data)
    elif trace_file:
        path = Path(trace_file).expanduser().resolve()
        source = str(path)
        if not path.exists():
            raise FileNotFoundError(f"Trace file not found: {path}")
        raw_data = json.loads(path.read_text())
        detected_format = TraceParser.detect_format(raw_data)
        trace = parse_trace_file(path)
    else:
        raise ValueError("Provide either trace_file or trace_json")

    normalized = TraceNormalizer.normalize(trace)
    return normalized, source, detected_format


def analyze_trace(
    trace_file: str | None = None,
    trace_json: dict[str, Any] | str | None = None,
    deterministic_only: bool = False,
    model: str | None = None,
    output_format: str = "markdown",
) -> dict[str, Any]:
    """Run full trace analysis and return structured result."""
    trace, source, detected_format = resolve_trace(trace_file=trace_file, trace_json=trace_json)
    cfg = get_config()

    used_fallback = False
    fallback_reason = ""
    if deterministic_only:
        analysis = run_analysis_without_llm(trace)
    elif not cfg.openrouter_api_key:
        used_fallback = True
        fallback_reason = "OPENROUTER_API_KEY not configured"
        analysis = run_analysis_without_llm(trace)
    else:
        try:
            analysis = run_analysis(trace, model=model, verbose=False)
            if not analysis.success:
                used_fallback = True
                fallback_reason = analysis.error or "LLM analysis returned unsuccessful result"
                analysis = run_analysis_without_llm(trace)
        except Exception as exc:
            used_fallback = True
            fallback_reason = str(exc)
            analysis = run_analysis_without_llm(trace)

    report_generator = ReportGenerator(trace, analysis)
    autopsy_report = report_generator.generate()
    rendered_report = report_generator.render(output_format)

    return {
        "source": source,
        "format": detected_format,
        "run_id": trace.run_id,
        "status": trace.status.value,
        "analysis_mode": "deterministic" if deterministic_only or used_fallback else "llm",
        "used_fallback": used_fallback,
        "fallback_reason": fallback_reason,
        "output_format": output_format,
        "report": rendered_report,
        "report_summary": autopsy_report.summary,
        "health_score": autopsy_report.health_score,
        "trace_summary": analysis.trace_summary,
        "preanalysis": analysis.preanalysis,
    }


def detect_patterns(
    trace_file: str | None = None,
    trace_json: dict[str, Any] | str | None = None,
) -> dict[str, Any]:
    """Detect deterministic patterns from a trace."""
    trace, source, detected_format = resolve_trace(trace_file=trace_file, trace_json=trace_json)
    patterns = PatternDetector(trace).detect_all()
    return {
        "source": source,
        "format": detected_format,
        "run_id": trace.run_id,
        "status": trace.status.value,
        "count": len(patterns),
        "patterns": [
            {
                "type": p.pattern_type.value,
                "severity": p.severity.value,
                "message": p.message,
                "evidence": p.evidence,
                "event_ids": p.event_ids,
                "metadata": p.metadata,
            }
            for p in patterns
        ],
    }


def validate_trace(
    trace_file: str | None = None,
    trace_json: dict[str, Any] | str | None = None,
) -> dict[str, Any]:
    """Validate trace parseability and schema structure."""
    trace, source, detected_format = resolve_trace(trace_file=trace_file, trace_json=trace_json)
    issues = TraceNormalizer.validate(trace)
    return {
        "source": source,
        "format": detected_format,
        "run_id": trace.run_id,
        "valid": len(issues) == 0,
        "issues": issues,
        "event_count": len(trace.events),
        "status": trace.status.value,
    }


def get_trace_summary(
    trace_file: str | None = None,
    trace_json: dict[str, Any] | str | None = None,
) -> dict[str, Any]:
    """Get lightweight summary stats for a trace."""
    trace, source, detected_format = resolve_trace(trace_file=trace_file, trace_json=trace_json)
    summary = TraceNormalizer.get_summary(trace)
    return {
        "source": source,
        "format": detected_format,
        **summary,
    }


def compare_traces(
    trace_file_a: str | None = None,
    trace_json_a: dict[str, Any] | str | None = None,
    trace_file_b: str | None = None,
    trace_json_b: dict[str, Any] | str | None = None,
) -> dict[str, Any]:
    """Compare two traces and return summary/pattern diffs."""
    trace_a, source_a, format_a = resolve_trace(trace_file=trace_file_a, trace_json=trace_json_a)
    trace_b, source_b, format_b = resolve_trace(trace_file=trace_file_b, trace_json=trace_json_b)

    summary_a = TraceNormalizer.get_summary(trace_a)
    summary_b = TraceNormalizer.get_summary(trace_b)
    numeric_keys = ["total_events", "llm_calls", "tool_calls", "errors", "total_tokens", "duration_ms"]
    metric_delta: dict[str, int | None] = {}
    for key in numeric_keys:
        av = summary_a.get(key)
        bv = summary_b.get(key)
        if isinstance(av, int) and isinstance(bv, int):
            metric_delta[key] = bv - av
        else:
            metric_delta[key] = None

    patterns_a = PatternDetector(trace_a).detect_all()
    patterns_b = PatternDetector(trace_b).detect_all()
    counts_a = _pattern_counts(patterns_a)
    counts_b = _pattern_counts(patterns_b)
    advanced = compare_traces_advanced(trace_a, trace_b)

    return {
        "trace_a": {"source": source_a, "format": format_a, "run_id": trace_a.run_id, "status": trace_a.status.value},
        "trace_b": {"source": source_b, "format": format_b, "run_id": trace_b.run_id, "status": trace_b.status.value},
        "status_changed": trace_a.status.value != trace_b.status.value,
        "metric_delta": metric_delta,
        "pattern_counts_a": counts_a,
        "pattern_counts_b": counts_b,
        **advanced.to_dict(),
    }


def capture_trace(
    trace_dir: str | None = None,
    enabled: bool = True,
    max_chars: int | None = None,
) -> dict[str, Any]:
    """
    Update in-process trace-capture settings.

    Note:
        This updates runtime config for the current process and is not persisted
        to disk-level environment files.
    """
    cfg = get_config()
    if trace_dir:
        cfg.trace_dir = Path(trace_dir).expanduser().resolve()
    cfg.trace_enabled = bool(enabled)
    if max_chars is not None:
        cfg.trace_max_chars = int(max_chars)

    cfg.trace_dir.mkdir(parents=True, exist_ok=True)
    active_trace_cfg = get_trace_config()

    return {
        "trace_enabled": cfg.trace_enabled,
        "trace_dir": str(cfg.trace_dir),
        "trace_max_chars": cfg.trace_max_chars,
        "effective_callback_config": {
            "enabled": active_trace_cfg.enabled,
            "trace_dir": str(active_trace_cfg.trace_dir),
            "max_chars": active_trace_cfg.max_chars,
        },
        "note": "Runtime config updated for current process only",
    }


def list_traces(
    directory: str | None = None,
    status: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """List available trace files with basic metadata."""
    cfg = get_config()
    trace_dir = Path(directory).expanduser().resolve() if directory else cfg.trace_dir.resolve()
    if not trace_dir.exists():
        return {"directory": str(trace_dir), "count": 0, "traces": []}

    start_date = _parse_date(date_from) if date_from else None
    end_date = _parse_date(date_to) if date_to else None
    normalized_status = status.lower() if status else None

    results: list[dict[str, Any]] = []
    for path in sorted(trace_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            raw = json.loads(path.read_text())
            run_id = str(raw.get("run_id") or raw.get("id") or path.stem)
            run_status = str(raw.get("status", "unknown")).lower()
            start_raw = raw.get("timestamp_start") or raw.get("start_time") or raw.get("startTime")
            parsed_start = _parse_datetime(start_raw)

            if normalized_status and run_status != normalized_status:
                continue
            if start_date and parsed_start and parsed_start.date() < start_date:
                continue
            if end_date and parsed_start and parsed_start.date() > end_date:
                continue

            events = raw.get("events")
            total_events = len(events) if isinstance(events, list) else None

            results.append(
                {
                    "run_id": run_id,
                    "status": run_status,
                    "path": str(path),
                    "size_bytes": path.stat().st_size,
                    "modified_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
                    "timestamp_start": parsed_start.isoformat() if parsed_start else None,
                    "total_events": total_events,
                }
            )
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            continue
        if len(results) >= max(1, limit):
            break

    return {"directory": str(trace_dir), "count": len(results), "traces": results}


def get_event_details(
    trace_file: str | None = None,
    trace_json: dict[str, Any] | str | None = None,
    event_id: int | None = None,
    start_id: int | None = None,
    end_id: int | None = None,
) -> dict[str, Any]:
    """Get specific event details from a trace."""
    trace, source, detected_format = resolve_trace(trace_file=trace_file, trace_json=trace_json)

    events: list[TraceEvent]
    if event_id is not None:
        event = trace.get_event(event_id)
        events = [event] if event else []
    else:
        start = 0 if start_id is None else start_id
        end = (len(trace.events) - 1) if end_id is None else end_id
        events = trace.get_events_in_range(start, end)

    return {
        "source": source,
        "format": detected_format,
        "run_id": trace.run_id,
        "count": len(events),
        "events": [_serialize_event(event) for event in events],
    }


def suggest_fixes(
    trace_file: str | None = None,
    trace_json: dict[str, Any] | str | None = None,
) -> dict[str, Any]:
    """Return categorized, actionable fix suggestions for a trace."""
    trace, source, detected_format = resolve_trace(trace_file=trace_file, trace_json=trace_json)
    preanalysis = RootCauseBuilder(trace).build()
    summary = TraceNormalizer.get_summary(trace)
    report = ReportGenerator(
        trace,
        AnalysisResult(
            report="",
            trace_summary=summary,
            preanalysis=preanalysis.to_dict(),
            success=True,
        ),
    ).generate()
    generated = FixSuggestionGenerator(trace, preanalysis).to_dict()

    plugin_manager = get_plugin_manager()
    plugin_fixes: list[dict[str, Any]] = []
    for plugin in plugin_manager.fix_generators:
        try:
            payload = plugin.generate(trace, preanalysis)
            plugin_fixes.append(
                {
                    "plugin": getattr(plugin, "name", plugin.__class__.__name__),
                    "payload": payload,
                }
            )
        except Exception:
            continue

    return {
        "source": source,
        "format": detected_format,
        "run_id": trace.run_id,
        "status": trace.status.value,
        "fix_recommendations": report.fix_recommendations,
        "generated_fix_suggestions": generated,
        "plugin_fix_suggestions": plugin_fixes,
        "top_hypotheses": [
            {
                "hypothesis": h.description,
                "confidence": h.confidence,
                "category": h.category,
                "supporting_events": h.supporting_events,
            }
            for h in preanalysis.hypotheses[:5]
        ],
    }


def health_check(
    trace_file: str | None = None,
    trace_json: dict[str, Any] | str | None = None,
) -> dict[str, Any]:
    """Return a compact health score with one-line summary."""
    trace, source, detected_format = resolve_trace(trace_file=trace_file, trace_json=trace_json)
    preanalysis = RootCauseBuilder(trace).build()
    summary = TraceNormalizer.get_summary(trace)
    report = ReportGenerator(
        trace,
        AnalysisResult(
            report="",
            trace_summary=summary,
            preanalysis=preanalysis.to_dict(),
            success=True,
        ),
    ).generate()

    top_signal = preanalysis.signals[0].type if preanalysis.signals else "none"
    one_line = (
        f"Health {report.health_score}/100: top signal '{top_signal}', "
        f"status '{trace.status.value}', events {len(trace.events)}."
    )
    return {
        "source": source,
        "format": detected_format,
        "run_id": trace.run_id,
        "health_score": report.health_score,
        "summary": one_line,
        "status": trace.status.value,
    }


def benchmark_runs(
    trace_files: list[str] | None = None,
    directory: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """Run benchmark/evaluation mode over trace files."""
    if trace_files:
        result = benchmark_traces(trace_files)
    else:
        trace_dir = directory or str(get_config().trace_dir)
        result = benchmark_trace_directory(trace_dir, limit=limit)
    return result.to_dict()


def monitor_traces(
    trace_dir: str | None = None,
    duration_seconds: float = 5.0,
    poll_interval_seconds: float = 1.0,
    max_alerts: int = 100,
) -> dict[str, Any]:
    """Run live trace monitoring for a bounded interval and return alerts."""
    monitor = LiveTraceMonitor(
        trace_dir=trace_dir or get_config().trace_dir,
        poll_interval_seconds=poll_interval_seconds,
    )
    alerts = []
    for alert in monitor.stream(duration_seconds=duration_seconds):
        alerts.append(
            {
                "trace_file": alert.trace_file,
                "run_id": alert.run_id,
                "pattern_type": alert.pattern_type,
                "severity": alert.severity,
                "message": alert.message,
                "event_ids": alert.event_ids,
            }
        )
        if len(alerts) >= max_alerts:
            break
    return {
        "trace_dir": str(monitor.trace_dir),
        "duration_seconds": duration_seconds,
        "alerts": alerts,
        "alert_count": len(alerts),
    }


def conversation_flow(
    trace_file: str | None = None,
    trace_json: dict[str, Any] | str | None = None,
) -> dict[str, Any]:
    """Build inter-agent conversation/handoff flow view."""
    trace, source, detected_format = resolve_trace(trace_file=trace_file, trace_json=trace_json)
    agents = trace.get_agent_ids()
    handoffs = trace.get_agent_handoffs()
    edges: dict[tuple[str, str], int] = {}
    for _, src, dst in handoffs:
        key = (src, dst)
        edges[key] = edges.get(key, 0) + 1

    return {
        "source": source,
        "format": detected_format,
        "run_id": trace.run_id,
        "agents": agents,
        "handoff_count": len(handoffs),
        "handoffs": [
            {"event_id": event_id, "from_agent": src, "to_agent": dst}
            for event_id, src, dst in handoffs
        ],
        "flow_edges": [
            {"from_agent": src, "to_agent": dst, "count": count}
            for (src, dst), count in sorted(edges.items(), key=lambda item: item[1], reverse=True)
        ],
    }


def recent_traces_resource(limit: int = 20) -> dict[str, Any]:
    """Resource payload for recent traces."""
    return list_traces(limit=limit)


def report_archive_resource(limit: int = 50) -> dict[str, Any]:
    """Resource payload for historical report index."""
    index_path = Path("./reports/index.json").resolve()
    if not index_path.exists():
        return {"path": str(index_path), "count": 0, "reports": []}

    data = json.loads(index_path.read_text())
    reports = data if isinstance(data, list) else []
    return {
        "path": str(index_path),
        "count": min(len(reports), limit),
        "reports": reports[:limit],
    }


def pattern_catalog_resource() -> dict[str, Any]:
    """Resource payload for known pattern types."""
    descriptions = {
        PatternType.INFINITE_LOOP.value: "Identical tool calls repeated consecutively.",
        PatternType.RETRY_STORM.value: "High-frequency retries with similar inputs.",
        PatternType.CONTEXT_OVERFLOW.value: "Total token usage exceeds effective context limit.",
        PatternType.HALLUCINATED_TOOL.value: "Tool call references a tool not in allow-list.",
        PatternType.EMPTY_RESPONSE.value: "LLM or tool call returned empty output.",
        PatternType.ERROR_CASCADE.value: "Errors cluster and propagate through execution.",
        PatternType.GOAL_DRIFT.value: "Execution behavior drifts away from original objective.",
        PatternType.STALE_CONTEXT.value: "Agent behavior does not adapt to changed tool outputs.",
        PatternType.TOKEN_WASTE.value: "High token spend with low useful transition ratio.",
        PatternType.AUTH_PERMISSION_FAILURE.value: "Repeated auth/permission failures (e.g. unauthorized/forbidden).",
        PatternType.TIMEOUT_PATTERN.value: "Timeout errors or slow-call bottlenecks dominate execution.",
        PatternType.REDUNDANT_TOOL_CALL.value: "Duplicate tool+input calls at separate points in trace.",
        PatternType.TOOL_CONTRACT_MISMATCH.value: "Tool IO does not match declared contract.",
    }
    return {"patterns": [{"type": p.value, "description": descriptions.get(p.value, "")} for p in PatternType]}


def config_resource() -> dict[str, Any]:
    """Resource payload for current application config."""
    cfg = get_config()
    return cfg.to_dict()


def plugin_resource() -> dict[str, Any]:
    """Resource payload for active plugin registry."""
    pm = get_plugin_manager()
    return {
        "parsers": [getattr(plugin, "name", plugin.__class__.__name__) for plugin in pm.parsers],
        "pattern_detectors": [getattr(plugin, "name", plugin.__class__.__name__) for plugin in pm.pattern_detectors],
        "report_templates": [getattr(plugin, "format_name", plugin.__class__.__name__) for plugin in pm.report_templates],
        "fix_generators": [getattr(plugin, "name", plugin.__class__.__name__) for plugin in pm.fix_generators],
        "visualizations": [getattr(plugin, "name", plugin.__class__.__name__) for plugin in pm.visualizations],
        "errors": pm.errors,
    }


def debug_my_agent_prompt(trace_reference: str = "") -> str:
    """Prompt template: debug my agent workflow."""
    hint = f"Trace reference: {trace_reference}\n" if trace_reference else ""
    return (
        f"{hint}"
        "Use `list_traces` (if needed) then `analyze_trace` on the most relevant trace. "
        "Explain the root cause with event citations, then call `suggest_fixes` and propose a minimal patch plan."
    )


def quick_health_check_prompt(trace_reference: str = "") -> str:
    """Prompt template: quick health check workflow."""
    hint = f"Trace reference: {trace_reference}\n" if trace_reference else ""
    return (
        f"{hint}"
        "Run `health_check` first, then `detect_patterns` for details. "
        "Answer with a one-line healthy/unhealthy verdict and top 3 risks."
    )


def compare_runs_prompt(trace_a: str = "", trace_b: str = "") -> str:
    """Prompt template: compare two runs workflow."""
    return (
        f"Compare trace A '{trace_a}' with trace B '{trace_b}' using `compare_traces`. "
        "Summarize what improved, what regressed, and what changed in pattern profile."
    )


def explain_failure_prompt(trace_reference: str = "", event_id: int | None = None) -> str:
    """Prompt template: explain a failure deeply."""
    focus = f" Focus around event {event_id}." if event_id is not None else ""
    return (
        f"Analyze trace '{trace_reference}' with `analyze_trace`, then use `get_event_details` for evidence.{focus} "
        "Provide a concise root-cause chain and concrete implementation fixes."
    )


def _pattern_counts(patterns: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for pattern in patterns:
        key = pattern.pattern_type.value
        counts[key] = counts.get(key, 0) + 1
    return counts


def _serialize_event(event: TraceEvent) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "parent_event_id": event.parent_event_id,
        "span_id": event.span_id,
        "agent_id": event.agent_id,
        "type": event.type.value,
        "role": event.role.value if event.role else None,
        "name": event.name,
        "input": event.input,
        "output": event.output,
        "token_count": event.token_count,
        "latency_ms": event.latency_ms,
        "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        "error": {
            "message": event.error.message,
            "stack": event.error.stack,
            "category": event.error.category,
        } if event.error else None,
        "metadata": event.metadata,
    }


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        if value > 1e12:
            return datetime.fromtimestamp(value / 1000)
        return datetime.fromtimestamp(value)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _parse_date(value: str) -> date:
    parsed = datetime.fromisoformat(value).date()
    return parsed
