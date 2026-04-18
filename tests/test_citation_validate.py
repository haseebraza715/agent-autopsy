"""Citation validation for LLM reports."""

from src.analysis.citation_validate import validate_report_event_citations
from src.ingestion import TraceNormalizer, parse_trace_file
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_validate_report_rejects_bad_event_id():
    trace = TraceNormalizer.normalize(parse_trace_file(REPO / "examples/traces/successful_run.json"))
    report = "See Event 99999 for the smoking gun."
    errs = validate_report_event_citations(report, trace)
    assert errs


def test_validate_report_accepts_existing_ids():
    trace = TraceNormalizer.normalize(parse_trace_file(REPO / "examples/traces/successful_run.json"))
    ids = [e.event_id for e in trace.events[:3]]
    report = f"Events {ids[0]} and {ids[1]} show the issue."
    errs = validate_report_event_citations(report, trace)
    assert not errs
