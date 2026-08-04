"""Structured LLM JSON extraction and validation."""

from pathlib import Path

from agent_autopsy.analysis.structured_report import (
    extract_structured_json,
    structured_to_markdown_append,
    validate_structured_against_trace,
)
from agent_autopsy.ingestion import TraceNormalizer, parse_trace_file

REPO = Path(__file__).resolve().parents[1]


def test_extract_and_validate_ok():
    md = """# Report
ok

```json
{"root_cause": "loop", "evidence": [{"description": "x", "event_ids": [1]}], "recommendations": ["fix"], "confidence": 0.9}
```
"""
    s = extract_structured_json(md)
    assert s is not None
    trace = TraceNormalizer.normalize(parse_trace_file(REPO / "examples/traces/successful_run.json"))
    errs = validate_structured_against_trace(s, trace)
    assert not errs
    appendix = structured_to_markdown_append(s, [])
    assert "loop" in appendix
    assert "Structured summary" in appendix


def test_validate_catches_bad_event():
    md = """```json
{"root_cause": "x", "evidence": [{"description": "bad", "event_ids": [99999]}], "recommendations": [], "confidence": 0.5}
```"""
    s = extract_structured_json(md)
    assert s is not None
    trace = TraceNormalizer.normalize(parse_trace_file(REPO / "examples/traces/successful_run.json"))
    errs = validate_structured_against_trace(s, trace)
    assert errs
