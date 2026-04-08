"""Tests for analysis-agent quality validation helpers."""

from src.analysis.agent import ReportQualityValidator


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
