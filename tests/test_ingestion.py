"""Tests for the ingestion module."""

import pytest
import json
from pathlib import Path

from src.ingestion import parse_trace_file, TraceNormalizer
from src.ingestion.parser import TraceParser
from src.ingestion.formats.langgraph import LangGraphParser
from src.ingestion.formats.generic import GenericJSONParser
from src.ingestion.formats.langchain import LangChainParser
from src.ingestion.formats.opentelemetry import OpenTelemetryParser
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
        assert len(trace.events) == 11
        assert len(trace.get_tool_calls()) == 7
        assert trace.stats.num_errors >= 1
        assert trace.error_summary is not None

    def test_parse_successful_trace(self):
        """Test parsing a successful trace."""
        trace_path = SAMPLE_TRACES_DIR / "successful_run.json"

        if not trace_path.exists():
            pytest.skip("Sample trace not found")

        trace = parse_trace_file(trace_path)

        assert trace.run_id == "run_success_001"
        assert trace.status == TraceStatus.SUCCESS
        assert len(trace.events) == 8
        assert trace.final_output == "25 * 4 = 100, which is 0x64 in hexadecimal."


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
        assert normalized.stats.num_llm_calls == 3
        assert normalized.stats.num_tool_calls == 2
        assert normalized.stats.num_errors == 0
        assert normalized.stats.total_tokens == 300
        assert normalized.stats.total_latency_ms == 1130

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
        assert summary["total_events"] == 11
        assert summary["tool_calls"] == 7
        assert summary["errors"] >= 1


class TestAdditionalFormatParsers:
    """Tests for dedicated LangChain/OpenTelemetry parser behavior."""

    def test_detect_format_prefers_langchain_when_runs_have_run_type(self):
        data = {
            "runs": [
                {"id": "r1", "run_type": "chain"},
                {"id": "r2", "run_type": "tool"},
            ]
        }
        assert TraceParser.detect_format(data) == "langchain"

    def test_parse_langchain_run_trace(self):
        """LangChain parser should map run_type to normalized event types."""
        parser = LangChainParser()
        data = {
            "run_id": "lc-run-1",
            "run_type": "chain",
            "name": "root_chain",
            "start_time": "2024-01-01T00:00:00Z",
            "end_time": "2024-01-01T00:00:01Z",
            "tools": [{"name": "search"}],
            "child_runs": [
                {
                    "id": "child-tool-1",
                    "run_type": "tool",
                    "name": "search",
                    "inputs": {"query": "agent autopsy"},
                    "outputs": {"result": "ok"},
                    "start_time": "2024-01-01T00:00:00Z",
                    "end_time": "2024-01-01T00:00:00.500Z",
                }
            ],
        }

        assert parser.can_parse(data)
        trace = parser.parse(data)

        assert trace.run_id == "lc-run-1"
        assert trace.env.agent_framework == "langchain"
        assert len(trace.events) == 2
        assert trace.events[0].type == EventType.DECISION
        assert trace.events[1].type == EventType.TOOL_CALL

    def test_parse_langchain_runs_parent_links_and_retriever(self):
        parser = LangChainParser()
        data = {
            "run_id": "lc-run-2",
            "runs": [
                {
                    "id": "child-1",
                    "parent_run_id": "root-1",
                    "run_type": "retriever",
                    "name": "kb_lookup",
                    "inputs": {"query": "budget"},
                    "outputs": {"docs": ["doc-1"]},
                    "usage_metadata": {"total_tokens": 18},
                },
                {
                    "id": "root-1",
                    "run_type": "chain",
                    "name": "planner",
                    "inputs": {"input": "Create a budget plan"},
                    "outputs": {"result": "done"},
                },
            ],
        }

        trace = parser.parse(data)
        trace = TraceNormalizer.normalize(trace)
        root = next(e for e in trace.events if e.name == "planner")
        child = next(e for e in trace.events if e.name == "kb_lookup")

        assert child.type == EventType.TOOL_CALL
        assert child.parent_event_id == root.event_id
        assert child.token_count == 18

    def test_parse_langchain_callback_trace(self):
        parser = LangChainParser()
        data = {
            "run_id": "lc-cb-1",
            "callbacks": [
                {
                    "event": "on_chain_start",
                    "run_id": "chain-1",
                    "name": "root_chain",
                    "input": {"input": "hello"},
                    "timestamp": "2024-01-01T00:00:00Z",
                },
                {
                    "event": "on_tool_end",
                    "run_id": "tool-1",
                    "parent_run_id": "chain-1",
                    "name": "search",
                    "output": {"result": "ok"},
                    "duration_ms": 120,
                },
            ],
        }

        trace = parser.parse(data)
        trace = TraceNormalizer.normalize(trace)

        assert len(trace.events) == 2
        assert trace.events[0].type == EventType.DECISION
        assert trace.events[1].type == EventType.TOOL_CALL
        assert trace.events[1].parent_event_id == trace.events[0].event_id

    def test_parse_opentelemetry_spans(self):
        """OpenTelemetry parser should parse OTLP-style spans into events."""
        parser = OpenTelemetryParser()
        data = {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": "agent-service"}},
                            {"key": "gen_ai.model", "value": {"stringValue": "gpt-4o"}},
                        ]
                    },
                    "scopeSpans": [
                        {
                            "spans": [
                                {
                                    "traceId": "trace-1",
                                    "spanId": "span-1",
                                    "name": "llm.chat.completion",
                                    "startTimeUnixNano": 1704067200000000000,
                                    "endTimeUnixNano": 1704067201000000000,
                                    "attributes": [
                                        {"key": "gen_ai.prompt", "value": {"stringValue": "Hello"}},
                                        {"key": "gen_ai.response", "value": {"stringValue": "Hi"}},
                                        {"key": "gen_ai.usage.total_tokens", "value": {"intValue": 42}},
                                    ],
                                    "status": {"code": 1},
                                }
                            ]
                        }
                    ],
                }
            ]
        }

        assert parser.can_parse(data)
        trace = parser.parse(data)

        assert trace.trace_id == "trace-1"
        assert trace.env.model == "gpt-4o"
        assert len(trace.events) == 1
        assert trace.events[0].type == EventType.LLM_CALL
        assert trace.events[0].token_count == 42

    def test_parse_opentelemetry_parent_links_and_genai_attributes(self):
        parser = OpenTelemetryParser()
        data = {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": "agent-service"}},
                            {"key": "gen_ai.model", "value": {"stringValue": "gpt-4.1-mini"}},
                            {"key": "gen_ai.max_input_tokens", "value": {"intValue": 64000}},
                        ]
                    },
                    "scopeSpans": [
                        {
                            "spans": [
                                {
                                    "traceId": "trace-otel-1",
                                    "spanId": "root-span",
                                    "name": "agent.router",
                                    "startTimeUnixNano": 1704067200000000000,
                                    "endTimeUnixNano": 1704067200200000000,
                                    "attributes": [
                                        {"key": "gen_ai.prompt", "value": {"stringValue": "Find revenue by quarter"}},
                                    ],
                                    "status": {"code": 1},
                                },
                                {
                                    "traceId": "trace-otel-1",
                                    "spanId": "child-span",
                                    "parentSpanId": "root-span",
                                    "name": "tool.search",
                                    "startTimeUnixNano": 1704067200300000000,
                                    "endTimeUnixNano": 1704067200800000000,
                                    "attributes": [
                                        {"key": "tool.name", "value": {"stringValue": "search"}},
                                        {"key": "gen_ai.usage.total_tokens", "value": {"intValue": 77}},
                                        {"key": "gen_ai.response", "value": {"stringValue": "found data"}},
                                    ],
                                    "status": {"code": "STATUS_CODE_ERROR", "message": "timed out"},
                                },
                            ]
                        }
                    ],
                }
            ]
        }

        trace = parser.parse(data)
        trace = TraceNormalizer.normalize(trace)
        root = next(e for e in trace.events if e.span_id == "root-span")
        child = next(e for e in trace.events if e.span_id == "child-span")

        assert trace.env.context_window_tokens == 64000
        assert child.parent_event_id == root.event_id
        assert child.type == EventType.TOOL_CALL
        assert child.token_count == 77
        assert child.error is not None
