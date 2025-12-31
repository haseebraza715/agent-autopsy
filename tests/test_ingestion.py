"""Tests for the ingestion module."""

import pytest
import json
from pathlib import Path

from src.ingestion import parse_trace_file, TraceNormalizer
from src.ingestion.formats.langgraph import LangGraphParser
from src.ingestion.formats.generic import GenericJSONParser
from src.schema import TraceStatus, EventType


SAMPLE_TRACES_DIR = Path(__file__).parent / "sample_traces"


class TestLangGraphParser:
    """Tests for LangGraph trace parsing."""

    def test_can_parse_langgraph_trace(self):
        """Test format detection for LangGraph traces."""
        parser = LangGraphParser()

        # Should recognize LangGraph format
        assert parser.can_parse({"thread_id": "123"})
        assert parser.can_parse({"runs": []})
        assert parser.can_parse({"checkpoint": {}})

        # Should not recognize other formats
        assert not parser.can_parse({"random": "data"})

    def test_parse_loop_failure_trace(self):
        """Test parsing a loop failure trace."""
        trace_path = SAMPLE_TRACES_DIR / "loop_failure.json"

        if not trace_path.exists():
            pytest.skip("Sample trace not found")

        trace = parse_trace_file(trace_path)

        assert trace.run_id == "run_loop_001"
        assert trace.status == TraceStatus.FAILED
        assert len(trace.events) > 0
        assert trace.error_summary is not None

    def test_parse_successful_trace(self):
        """Test parsing a successful trace."""
        trace_path = SAMPLE_TRACES_DIR / "successful_run.json"

        if not trace_path.exists():
            pytest.skip("Sample trace not found")

        trace = parse_trace_file(trace_path)

        assert trace.run_id == "run_success_001"
        assert trace.status == TraceStatus.SUCCESS
        assert trace.final_output is not None


class TestGenericParser:
    """Tests for generic JSON parsing."""

    def test_can_parse_any_dict(self):
        """Test that generic parser accepts any dict."""
        parser = GenericJSONParser()
        assert parser.can_parse({})
        assert parser.can_parse({"anything": "goes"})

    def test_parse_minimal_trace(self):
        """Test parsing a minimal trace structure."""
        parser = GenericJSONParser()

        data = {
            "id": "test-123",
            "status": "success",
            "events": [
                {"type": "message", "content": "Hello"},
                {"type": "tool", "name": "search", "input": "query"},
            ],
        }

        trace = parser.parse(data)

        assert trace.run_id == "test-123"
        assert trace.status == TraceStatus.SUCCESS
        assert len(trace.events) == 2


class TestTraceNormalizer:
    """Tests for trace normalization."""

    def test_normalize_trace(self):
        """Test normalizing a parsed trace."""
        trace_path = SAMPLE_TRACES_DIR / "successful_run.json"

        if not trace_path.exists():
            pytest.skip("Sample trace not found")

        trace = parse_trace_file(trace_path)
        normalized = TraceNormalizer.normalize(trace)

        # Event IDs should be sequential
        for i, event in enumerate(normalized.events):
            assert event.event_id == i

        # Stats should be calculated
        assert normalized.stats.num_llm_calls >= 0
        assert normalized.stats.num_tool_calls >= 0

    def test_validate_trace(self):
        """Test trace validation."""
        trace_path = SAMPLE_TRACES_DIR / "successful_run.json"

        if not trace_path.exists():
            pytest.skip("Sample trace not found")

        trace = parse_trace_file(trace_path)
        issues = TraceNormalizer.validate(trace)

        # Well-formed traces should have no issues
        assert len(issues) == 0

    def test_get_summary(self):
        """Test getting trace summary."""
        trace_path = SAMPLE_TRACES_DIR / "loop_failure.json"

        if not trace_path.exists():
            pytest.skip("Sample trace not found")

        trace = parse_trace_file(trace_path)
        summary = TraceNormalizer.get_summary(trace)

        assert "run_id" in summary
        assert "status" in summary
        assert "total_events" in summary
        assert summary["status"] == "failed"
