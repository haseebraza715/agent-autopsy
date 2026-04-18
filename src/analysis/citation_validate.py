"""Validate that cited event IDs in an LLM report exist on the trace."""

from __future__ import annotations

import re

from src.schema import Trace

_EVENT_ID_RE = re.compile(r"\b(?:event|events)\s+(\d+)(?:\s*[-–]\s*(\d+))?\b", re.IGNORECASE)


def cited_event_ids_from_report(report: str) -> set[int]:
    """Extract event IDs mentioned in free-text report sections."""
    found: set[int] = set()
    for m in _EVENT_ID_RE.finditer(report or ""):
        a = int(m.group(1))
        found.add(a)
        if m.group(2):
            b = int(m.group(2))
            lo, hi = (a, b) if a <= b else (b, a)
            for i in range(lo, hi + 1):
                found.add(i)
    return found


def validate_report_event_citations(report: str, trace: Trace) -> list[str]:
    """
    Return a list of validation errors for non-existent event IDs.

    Empty list means every cited ID exists on the trace.
    """
    valid = {e.event_id for e in trace.events}
    cited = cited_event_ids_from_report(report)
    if not valid:
        return [f"Cited event {eid} not found (trace has no events)." for eid in sorted(cited)]
    vr = f"{min(valid)}–{max(valid)}"
    errors = [f"Cited event {eid} not found in trace (valid event id range: {vr})." for eid in sorted(cited) if eid not in valid]
    return errors
