"""Tests for analysis-agent quality validation helpers."""

from langchain_core.messages import AIMessageChunk

from src.analysis.agent import ReportQualityValidator
from src.analysis.llm_agent import AnalysisAgent


class TestReportQualityValidator:
    """Quality-gate validation tests."""

    def test_validate_high_quality_report(self):
        report = """
## Summary
The run failed at Event 14 due to repeated tool retries.

## Timeline
- Event 7: first timeout
- Events 12-14: repeated retries without backoff

## Root Cause Chain
Root cause: missing retry policy guard. Event 12 retried after the same timeout.

## Fix Recommendations
- Add exponential backoff and retry cap at the tool wrapper.
- Implement circuit breaker after 3 failures.

## Confidence
0.82 based on repeated evidence in Events 12-14.
"""
        quality = ReportQualityValidator.validate(report)

        assert quality["overall_score"] >= 0.7
        assert quality["has_event_citations"] is True
        assert quality["has_root_cause"] is True
        assert quality["has_fix_recommendations"] is True

    def test_validate_low_quality_report_and_feedback(self):
        report = "Agent failed. Needs improvement."
        quality = ReportQualityValidator.validate(report)
        feedback = ReportQualityValidator.build_feedback(quality)

        assert quality["overall_score"] < 0.5
        assert len(quality["missing_sections"]) >= 3
        assert "missing sections" in feedback.lower()


class TestAnalysisAgentStreamHelpers:
    """Helpers used by LangGraph streaming UI."""

    def test_stringify_stream_content(self) -> None:
        assert AnalysisAgent._stringify_stream_content("hi") == "hi"
        assert AnalysisAgent._stringify_stream_content(
            [{"type": "text", "text": "ab"}]
        ) == "ab"
        assert AnalysisAgent._stringify_stream_content(["x", "y"]) == "xy"

    def test_stream_chat_to_message_accumulates_chunks(self) -> None:
        """Runnable.stream chunks merge to a single AIMessage (no LangGraph writer)."""

        class _Runnable:
            def stream(self, _messages: object):
                yield AIMessageChunk(content="Hel")
                yield AIMessageChunk(content="lo")

        class _Dummy:
            def _optional_stream_writer(self):
                return None

        dummy = _Dummy()
        out = AnalysisAgent._stream_chat_to_message(dummy, _Runnable(), [], node_name="test")
        text = out.content if isinstance(out.content, str) else str(out.content)
        assert "Hello" in text
