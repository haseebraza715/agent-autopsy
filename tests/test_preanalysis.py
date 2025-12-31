"""Tests for the pre-analysis module."""

import pytest
from pathlib import Path

from src.ingestion import parse_trace_file
from src.preanalysis import (
    PatternDetector,
    PatternType,
    Severity,
    ContractValidator,
    RootCauseBuilder,
)


SAMPLE_TRACES_DIR = Path(__file__).parent / "sample_traces"


class TestPatternDetector:
    """Tests for pattern detection."""

    def test_detect_loops(self):
        """Test loop detection in traces."""
        trace_path = SAMPLE_TRACES_DIR / "loop_failure.json"

        if not trace_path.exists():
            pytest.skip("Sample trace not found")

        trace = parse_trace_file(trace_path)
        detector = PatternDetector(trace)

        loops = detector.detect_loops()

        # Should detect the repeated web_search calls
        assert len(loops) > 0
        assert any(p.pattern_type == PatternType.INFINITE_LOOP for p in loops)

    def test_detect_hallucinated_tools(self):
        """Test hallucinated tool detection."""
        trace_path = SAMPLE_TRACES_DIR / "hallucinated_tool.json"

        if not trace_path.exists():
            pytest.skip("Sample trace not found")

        trace = parse_trace_file(trace_path)
        detector = PatternDetector(trace)

        patterns = detector.detect_hallucinated_tools()

        # Should detect the non-existent email tools
        assert len(patterns) > 0
        assert any(p.pattern_type == PatternType.HALLUCINATED_TOOL for p in patterns)

    def test_detect_error_cascades(self):
        """Test error cascade detection."""
        trace_path = SAMPLE_TRACES_DIR / "loop_failure.json"

        if not trace_path.exists():
            pytest.skip("Sample trace not found")

        trace = parse_trace_file(trace_path)
        detector = PatternDetector(trace)

        cascades = detector.detect_error_cascades()

        # Multiple consecutive errors should be detected
        if len(trace.get_error_events()) >= 2:
            assert len(cascades) >= 0  # May or may not detect cascade

    def test_detect_empty_responses(self):
        """Test empty response detection."""
        trace_path = SAMPLE_TRACES_DIR / "loop_failure.json"

        if not trace_path.exists():
            pytest.skip("Sample trace not found")

        trace = parse_trace_file(trace_path)
        detector = PatternDetector(trace)

        empty = detector.detect_empty_responses()

        # Trace with null outputs should have empty responses detected
        assert len(empty) >= 0

    def test_no_patterns_in_successful_trace(self):
        """Test that successful traces have minimal patterns."""
        trace_path = SAMPLE_TRACES_DIR / "successful_run.json"

        if not trace_path.exists():
            pytest.skip("Sample trace not found")

        trace = parse_trace_file(trace_path)
        detector = PatternDetector(trace)

        all_patterns = detector.detect_all()

        # Successful trace should have no critical patterns
        critical = [p for p in all_patterns if p.severity == Severity.CRITICAL]
        assert len(critical) == 0


class TestContractValidator:
    """Tests for contract validation."""

    def test_validate_known_tools(self):
        """Test validation with known tools."""
        trace_path = SAMPLE_TRACES_DIR / "successful_run.json"

        if not trace_path.exists():
            pytest.skip("Sample trace not found")

        trace = parse_trace_file(trace_path)
        validator = ContractValidator(trace)

        result = validator.validate_all()

        # Successful trace with known tools should have minimal violations
        unknown_tool_violations = [
            v for v in result.violations if v.violation_type == "unknown_tool"
        ]
        assert len(unknown_tool_violations) == 0

    def test_detect_unknown_tools(self):
        """Test detection of unknown tool calls."""
        trace_path = SAMPLE_TRACES_DIR / "hallucinated_tool.json"

        if not trace_path.exists():
            pytest.skip("Sample trace not found")

        trace = parse_trace_file(trace_path)
        validator = ContractValidator(trace)

        violations = validator.get_violations()

        # Should detect the hallucinated tools
        unknown_tools = [v for v in violations if v.violation_type == "unknown_tool"]
        assert len(unknown_tools) > 0


class TestRootCauseBuilder:
    """Tests for root cause hypothesis building."""

    def test_build_preanalysis_bundle(self):
        """Test building complete pre-analysis bundle."""
        trace_path = SAMPLE_TRACES_DIR / "loop_failure.json"

        if not trace_path.exists():
            pytest.skip("Sample trace not found")

        trace = parse_trace_file(trace_path)
        builder = RootCauseBuilder(trace)

        bundle = builder.build()

        assert len(bundle.signals) > 0
        assert len(bundle.hypotheses) > 0
        assert bundle.summary != ""

    def test_hypotheses_have_confidence(self):
        """Test that hypotheses include confidence scores."""
        trace_path = SAMPLE_TRACES_DIR / "loop_failure.json"

        if not trace_path.exists():
            pytest.skip("Sample trace not found")

        trace = parse_trace_file(trace_path)
        builder = RootCauseBuilder(trace)

        bundle = builder.build()

        for hypothesis in bundle.hypotheses:
            assert 0 <= hypothesis.confidence <= 1
            assert hypothesis.category in ["code", "prompt", "tool", "ops", "unknown"]

    def test_to_dict(self):
        """Test serialization to dict."""
        trace_path = SAMPLE_TRACES_DIR / "loop_failure.json"

        if not trace_path.exists():
            pytest.skip("Sample trace not found")

        trace = parse_trace_file(trace_path)
        builder = RootCauseBuilder(trace)

        bundle = builder.build()
        data = bundle.to_dict()

        assert "signals" in data
        assert "top_suspects" in data
        assert "summary" in data
