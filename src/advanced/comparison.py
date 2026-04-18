"""
Advanced trace comparison and regression detection utilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.preanalysis import PatternDetector
from src.schema import Trace, TraceEvent, EventType


@dataclass
class TraceComparisonResult:
    """Structured comparison output for two traces."""

    changed_tool_signatures: list[str]
    new_tool_signatures: list[str]
    removed_tool_signatures: list[str]
    changed_llm_outputs: list[dict[str, Any]]
    pattern_delta: dict[str, int]
    regressions: list[str]
    improvements: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "changed_tool_signatures": self.changed_tool_signatures,
            "new_tool_signatures": self.new_tool_signatures,
            "removed_tool_signatures": self.removed_tool_signatures,
            "changed_llm_outputs": self.changed_llm_outputs,
            "pattern_delta": self.pattern_delta,
            "regressions": self.regressions,
            "improvements": self.improvements,
        }


def compare_traces_advanced(trace_a: Trace, trace_b: Trace) -> TraceComparisonResult:
    """Compare traces for behavior changes and regressions."""
    tool_sigs_a = _tool_signatures(trace_a)
    tool_sigs_b = _tool_signatures(trace_b)
    tool_map_a = _tool_signature_map(trace_a)
    tool_map_b = _tool_signature_map(trace_b)

    changed_tool_sigs = sorted(
        tool_name
        for tool_name in (set(tool_map_a.keys()) & set(tool_map_b.keys()))
        if tool_map_a[tool_name] != tool_map_b[tool_name]
    )
    new_tool_sigs = sorted(set(tool_sigs_b) - set(tool_sigs_a))
    removed_tool_sigs = sorted(set(tool_sigs_a) - set(tool_sigs_b))

    llm_diffs = _compare_llm_outputs(trace_a, trace_b)

    counts_a = _pattern_counts(PatternDetector(trace_a).detect_all())
    counts_b = _pattern_counts(PatternDetector(trace_b).detect_all())
    pattern_delta = {
        key: counts_b.get(key, 0) - counts_a.get(key, 0)
        for key in sorted(set(counts_a.keys()) | set(counts_b.keys()))
    }
    regressions = [k for k, d in pattern_delta.items() if d > 0]
    improvements = [k for k, d in pattern_delta.items() if d < 0]

    return TraceComparisonResult(
        changed_tool_signatures=changed_tool_sigs,
        new_tool_signatures=new_tool_sigs,
        removed_tool_signatures=removed_tool_sigs,
        changed_llm_outputs=llm_diffs,
        pattern_delta=pattern_delta,
        regressions=regressions,
        improvements=improvements,
    )


def _tool_signatures(trace: Trace) -> list[str]:
    sigs = []
    for event in trace.get_tool_calls():
        sig = event.get_tool_signature()
        if sig:
            sigs.append(sig)
    return sigs


def _tool_signature_map(trace: Trace) -> dict[str, set[str]]:
    """Map tool name -> observed signature set for change detection."""
    mapped: dict[str, set[str]] = {}
    for event in trace.get_tool_calls():
        if not event.name:
            continue
        sig = event.get_tool_signature()
        if sig:
            mapped.setdefault(event.name, set()).add(sig)
    return mapped


def _compare_llm_outputs(trace_a: Trace, trace_b: Trace) -> list[dict[str, Any]]:
    events_a = [e for e in trace_a.events if e.type == EventType.LLM_CALL]
    events_b = [e for e in trace_b.events if e.type == EventType.LLM_CALL]
    diffs: list[dict[str, Any]] = []
    for idx in range(min(len(events_a), len(events_b))):
        out_a = str(events_a[idx].output)
        out_b = str(events_b[idx].output)
        if out_a != out_b:
            diffs.append(
                {
                    "pair_index": idx,
                    "event_id_a": events_a[idx].event_id,
                    "event_id_b": events_b[idx].event_id,
                    "output_a_preview": out_a[:240],
                    "output_b_preview": out_b[:240],
                }
            )
    return diffs


def _pattern_counts(patterns: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for pattern in patterns:
        key = pattern.pattern_type.value
        counts[key] = counts.get(key, 0) + 1
    return counts


def _pattern_type_set(patterns: list[Any]) -> set[str]:
    return {p.pattern_type.value for p in patterns}


def trace_diff_detail(trace_a: Trace, trace_b: Trace) -> dict[str, Any]:
    """
    Rich diff for CLI: event ID sets, pattern sets, tool signature changes, timing deltas.
    """
    ids_a = {e.event_id for e in trace_a.events}
    ids_b = {e.event_id for e in trace_b.events}

    pa = PatternDetector(trace_a).detect_all()
    pb = PatternDetector(trace_b).detect_all()
    pset_a = _pattern_type_set(pa)
    pset_b = _pattern_type_set(pb)

    tool_sigs_a = _tool_signatures(trace_a)
    tool_sigs_b = _tool_signatures(trace_b)

    timing_rows: list[dict[str, Any]] = []
    events_a = list(trace_a.events)
    events_b = list(trace_b.events)
    for idx in range(min(len(events_a), len(events_b))):
        ea, eb = events_a[idx], events_b[idx]
        da = ea.timestamp
        db = eb.timestamp
        delta_ms = None
        if da is not None and db is not None:
            delta_ms = (db - da).total_seconds() * 1000.0
        timing_rows.append(
            {
                "index": idx,
                "event_id_a": ea.event_id,
                "event_id_b": eb.event_id,
                "delta_ms": delta_ms,
            }
        )

    arg_diffs: list[dict[str, Any]] = []
    tc_a = trace_a.get_tool_calls()
    tc_b = trace_b.get_tool_calls()
    for idx in range(min(len(tc_a), len(tc_b))):
        if tc_a[idx].name != tc_b[idx].name:
            arg_diffs.append(
                {
                    "index": idx,
                    "event_a": tc_a[idx].event_id,
                    "event_b": tc_b[idx].event_id,
                    "tool_a": tc_a[idx].name,
                    "tool_b": tc_b[idx].name,
                }
            )
        elif str(tc_a[idx].input) != str(tc_b[idx].input):
            arg_diffs.append(
                {
                    "index": idx,
                    "event_a": tc_a[idx].event_id,
                    "event_b": tc_b[idx].event_id,
                    "tool": tc_a[idx].name,
                    "input_a_preview": str(tc_a[idx].input)[:200],
                    "input_b_preview": str(tc_b[idx].input)[:200],
                }
            )

    return {
        "run_id_a": trace_a.run_id,
        "run_id_b": trace_b.run_id,
        "event_ids_only_in_a": sorted(ids_a - ids_b),
        "event_ids_only_in_b": sorted(ids_b - ids_a),
        "patterns_only_in_a": sorted(pset_a - pset_b),
        "patterns_only_in_b": sorted(pset_b - pset_a),
        "tool_signatures_only_in_a": sorted(set(tool_sigs_a) - set(tool_sigs_b)),
        "tool_signatures_only_in_b": sorted(set(tool_sigs_b) - set(tool_sigs_a)),
        "tool_call_arg_or_name_diffs": arg_diffs,
        "timing_deltas_aligned_by_index": timing_rows,
        "advanced": compare_traces_advanced(trace_a, trace_b).to_dict(),
    }
