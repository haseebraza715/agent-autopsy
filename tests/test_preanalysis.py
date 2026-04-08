"""Tests for the pre-analysis module."""

from datetime import datetime, timedelta
import json
import tempfile
from pathlib import Path

from src.preanalysis import (
    PatternDetector,
    PatternType,
    Severity,
    ContractValidator,
    RootCauseBuilder,
)
from src.utils.config import get_config
from src.schema import (
    Trace,
    TraceEvent,
    TraceStatus,
    EventType,
    EnvironmentInfo,
    EventError,
    TaskContext,
)


def _build_trace(
    events: list[TraceEvent],
    *,
    tools_available: list[str] | None = None,
    status: TraceStatus = TraceStatus.SUCCESS,
    model: str = "gpt-4",
    context_window_tokens: int | None = None,
) -> Trace:
    """Create a normalized trace for deterministic unit tests."""
    trace = Trace(
        run_id="test-run",
        timestamp_start=datetime(2026, 1, 1, 0, 0, 0),
        timestamp_end=datetime(2026, 1, 1, 0, 1, 0),
        status=status,
        env=EnvironmentInfo(
            agent_framework="test",
            model=model,
            tools_available=tools_available or [],
            context_window_tokens=context_window_tokens,
        ),
        events=events,
    )
    trace.stats = trace.calculate_stats()
    return trace


class TestPatternDetector:
    """Tests for pattern detection."""

    def test_detect_loops(self):
        """Detect repeated identical tool calls as an infinite loop."""
        events = [
            TraceEvent(event_id=0, type=EventType.TOOL_CALL, name="search", input={"q": "x"}, output={"v": 1}),
            TraceEvent(event_id=1, type=EventType.TOOL_CALL, name="search", input={"q": "x"}, output={"v": 1}),
            TraceEvent(event_id=2, type=EventType.TOOL_CALL, name="search", input={"q": "x"}, output={"v": 1}),
        ]
        detector = PatternDetector(_build_trace(events, tools_available=["search"]))

        loops = detector.detect_loops()

        assert len(loops) == 1
        assert loops[0].pattern_type == PatternType.INFINITE_LOOP
        assert loops[0].severity == Severity.CRITICAL
        assert loops[0].metadata["count"] == 3
        assert loops[0].event_ids == [0, 1, 2]

    def test_detect_hallucinated_tools(self):
        """Detect tool calls not present in the declared tool allow-list."""
        events = [
            TraceEvent(event_id=0, type=EventType.TOOL_CALL, name="search", input={"q": "ok"}, output={"v": 1}),
            TraceEvent(event_id=1, type=EventType.TOOL_CALL, name="email_sender", input={"to": "x"}, output=None),
        ]
        detector = PatternDetector(_build_trace(events, tools_available=["search"]))

        patterns = detector.detect_hallucinated_tools()

        assert len(patterns) == 1
        assert patterns[0].pattern_type == PatternType.HALLUCINATED_TOOL
        assert patterns[0].event_ids == [1]

    def test_detect_error_cascades(self):
        """Detect grouped error events as a cascade."""
        events = [
            TraceEvent(event_id=0, type=EventType.MESSAGE, output="ok"),
            TraceEvent(event_id=1, type=EventType.ERROR, error=EventError(message="first error")),
            TraceEvent(event_id=3, type=EventType.ERROR, error=EventError(message="second error")),
            TraceEvent(event_id=8, type=EventType.ERROR, error=EventError(message="isolated error")),
        ]
        detector = PatternDetector(_build_trace(events, status=TraceStatus.FAILED))

        cascades = detector.detect_error_cascades()

        assert len(cascades) == 1
        assert cascades[0].pattern_type == PatternType.ERROR_CASCADE
        assert cascades[0].event_ids == [1, 3]
        assert cascades[0].metadata["cascade_length"] == 2

    def test_detect_empty_responses(self):
        """Detect empty outputs only for LLM/tool events."""
        events = [
            TraceEvent(event_id=0, type=EventType.LLM_CALL, name="gpt-4", output=""),
            TraceEvent(event_id=1, type=EventType.TOOL_CALL, name="search", output=None),
            TraceEvent(event_id=2, type=EventType.TOOL_CALL, name="search", output={}),
            TraceEvent(event_id=3, type=EventType.MESSAGE, output=None),  # ignored
            TraceEvent(event_id=4, type=EventType.LLM_CALL, name="gpt-4", output="non-empty"),
        ]
        detector = PatternDetector(_build_trace(events, tools_available=["search"]))

        empty = detector.detect_empty_responses()

        assert len(empty) == 1
        assert empty[0].pattern_type == PatternType.EMPTY_RESPONSE
        assert empty[0].event_ids == [0, 1, 2]

    def test_no_patterns_in_clean_trace(self):
        """A clean trace should not trigger pattern detections."""
        events = [
            TraceEvent(event_id=0, type=EventType.LLM_CALL, name="gpt-4", output="calling tool"),
            TraceEvent(
                event_id=1,
                type=EventType.TOOL_CALL,
                name="calculator",
                input={"expr": "2+2"},
                output={"result": 4},
            ),
            TraceEvent(event_id=2, type=EventType.LLM_CALL, name="gpt-4", output="done"),
        ]
        detector = PatternDetector(_build_trace(events, tools_available=["calculator"]))

        all_patterns = detector.detect_all()

        assert all_patterns == []

    def test_empty_trace_has_no_patterns(self):
        """Edge case: empty traces should not fail or emit false positives."""
        detector = PatternDetector(_build_trace([]))
        assert detector.detect_all() == []

    def test_single_event_trace_has_no_patterns(self):
        """Edge case: one event should not trigger any multi-event patterns."""
        events = [TraceEvent(event_id=0, type=EventType.MESSAGE, output="hello")]
        detector = PatternDetector(_build_trace(events))
        assert detector.detect_all() == []

    def test_large_trace_with_thousands_of_events(self):
        """Edge case: large traces should remain stable and avoid false positives."""
        start = datetime(2026, 1, 1, 0, 0, 0)
        events = [
            TraceEvent(
                event_id=i,
                type=EventType.MESSAGE,
                output=f"event-{i}",
                timestamp=start + timedelta(seconds=i),
            )
            for i in range(2000)
        ]
        detector = PatternDetector(_build_trace(events))

        all_patterns = detector.detect_all()

        assert all_patterns == []

    def test_detect_auth_permission_failures(self):
        events = [
            TraceEvent(event_id=0, type=EventType.ERROR, error=EventError(message="401 unauthorized")),
            TraceEvent(event_id=1, type=EventType.ERROR, error=EventError(message="403 forbidden")),
        ]
        detector = PatternDetector(_build_trace(events, status=TraceStatus.FAILED))

        patterns = detector.detect_auth_permission_failures()

        assert len(patterns) == 1
        assert patterns[0].pattern_type == PatternType.AUTH_PERMISSION_FAILURE
        assert patterns[0].event_ids == [0, 1]

    def test_auth_detector_ignores_plain_numeric_event_text(self):
        events = [
            TraceEvent(event_id=401, type=EventType.MESSAGE, output="event-401"),
            TraceEvent(event_id=403, type=EventType.MESSAGE, output="event-403"),
        ]
        detector = PatternDetector(_build_trace(events))
        assert detector.detect_auth_permission_failures() == []

    def test_detect_timeout_patterns(self):
        events = [
            TraceEvent(
                event_id=0,
                type=EventType.TOOL_CALL,
                name="search",
                latency_ms=125000,
                error=EventError(message="request timeout"),
            ),
            TraceEvent(
                event_id=1,
                type=EventType.TOOL_CALL,
                name="search",
                latency_ms=130000,
            ),
        ]
        detector = PatternDetector(_build_trace(events, tools_available=["search"], status=TraceStatus.FAILED))
        patterns = detector.detect_timeout_patterns()
        assert len(patterns) == 1
        assert patterns[0].pattern_type == PatternType.TIMEOUT_PATTERN
        assert set(patterns[0].event_ids) == {0, 1}

    def test_detect_redundant_tool_calls(self):
        events = [
            TraceEvent(event_id=0, type=EventType.TOOL_CALL, name="search", input={"q": "budget"}, output={"ok": 1}),
            TraceEvent(event_id=1, type=EventType.MESSAGE, output="thinking"),
            TraceEvent(event_id=2, type=EventType.TOOL_CALL, name="search", input={"q": "budget"}, output={"ok": 2}),
        ]
        detector = PatternDetector(_build_trace(events, tools_available=["search"]))
        patterns = detector.detect_redundant_tool_calls()
        assert len(patterns) == 1
        assert patterns[0].pattern_type == PatternType.REDUNDANT_TOOL_CALL
        assert patterns[0].event_ids == [0, 2]

    def test_detect_goal_drift(self):
        events = [
            TraceEvent(event_id=0, type=EventType.LLM_CALL, input="build quarterly budget", output="planning budget"),
            TraceEvent(event_id=1, type=EventType.TOOL_CALL, name="search", input="quarterly budget template", output="data"),
            TraceEvent(event_id=2, type=EventType.DECISION, input="budget plan"),
            TraceEvent(event_id=3, type=EventType.LLM_CALL, input="favorite movies list", output="movie ranking"),
            TraceEvent(event_id=4, type=EventType.TOOL_CALL, name="search", input="movie awards", output="awards"),
            TraceEvent(event_id=5, type=EventType.DECISION, input="movie summary"),
        ]
        trace = _build_trace(events, tools_available=["search"])
        trace.task = TaskContext(goal="Build a quarterly budget plan")
        detector = PatternDetector(trace)

        patterns = detector.detect_goal_drift()

        assert len(patterns) == 1
        assert patterns[0].pattern_type == PatternType.GOAL_DRIFT
        assert len(patterns[0].event_ids) >= 3

    def test_detect_stale_context(self):
        events = [
            TraceEvent(event_id=0, type=EventType.TOOL_CALL, name="search", input={"q": "weather"}, output={"temp": 22}),
            TraceEvent(event_id=1, type=EventType.TOOL_CALL, name="search", input={"q": "weather"}, output={"temp": 24}),
            TraceEvent(event_id=2, type=EventType.TOOL_CALL, name="search", input={"q": "weather"}, output={"temp": 25}),
        ]
        detector = PatternDetector(_build_trace(events, tools_available=["search"]))
        patterns = detector.detect_stale_context()
        assert len(patterns) == 1
        assert patterns[0].pattern_type == PatternType.STALE_CONTEXT

    def test_detect_token_waste(self):
        events = [
            TraceEvent(event_id=0, type=EventType.LLM_CALL, token_count=900, output="long reasoning"),
            TraceEvent(event_id=1, type=EventType.LLM_CALL, token_count=800, output="more reasoning"),
            TraceEvent(event_id=2, type=EventType.LLM_CALL, token_count=700, output="still reasoning"),
            TraceEvent(event_id=3, type=EventType.MESSAGE, output="no progress"),
        ]
        detector = PatternDetector(_build_trace(events))
        patterns = detector.detect_token_waste()
        assert len(patterns) == 1
        assert patterns[0].pattern_type == PatternType.TOKEN_WASTE
        assert patterns[0].metadata["total_llm_tokens"] == 2400

    def test_context_overflow_uses_trace_context_window_first(self):
        events = [
            TraceEvent(event_id=0, type=EventType.LLM_CALL, token_count=2500),
        ]
        detector = PatternDetector(_build_trace(events, context_window_tokens=2000))
        patterns = detector.detect_context_overflow()
        assert len(patterns) == 1
        assert patterns[0].metadata["threshold"] == 2000
        assert patterns[0].metadata["active_limit_source"] == "trace_context_window_tokens"

    def test_context_overflow_uses_external_model_limit_file(self):
        events = [TraceEvent(event_id=0, type=EventType.LLM_CALL, token_count=5000)]
        with tempfile.TemporaryDirectory() as tmpdir:
            limits_path = Path(tmpdir) / "limits.json"
            limits_path.write_text(json.dumps({"gpt-4": 4000}))
            cfg = get_config()
            original_path = cfg.model_context_limits_path
            cfg.model_context_limits_path = str(limits_path)
            PatternDetector._load_model_context_limits.cache_clear()

            detector = PatternDetector(_build_trace(events, model="gpt-4"))
            patterns = detector.detect_context_overflow()
            cfg.model_context_limits_path = original_path
            PatternDetector._load_model_context_limits.cache_clear()

        assert len(patterns) == 1
        assert patterns[0].metadata["threshold"] == 4000
        assert patterns[0].metadata["active_limit_source"] == "model_context_limits_config"


class TestContractValidator:
    """Tests for contract validation."""

    def test_validate_known_tools(self):
        """Known tool calls should not be flagged as unknown tools."""
        events = [
            TraceEvent(
                event_id=0,
                type=EventType.TOOL_CALL,
                name="search",
                input={"q": "agent autopsy"},
                output={"result": "ok"},
                latency_ms=20,
            )
        ]
        trace = _build_trace(events, tools_available=["search"])
        validator = ContractValidator(trace)

        result = validator.validate_all()

        unknown_tool_violations = [
            v for v in result.violations if v.violation_type == "unknown_tool"
        ]
        assert unknown_tool_violations == []

    def test_detect_unknown_tools(self):
        """Unknown tool calls should be surfaced as contract violations."""
        events = [
            TraceEvent(
                event_id=42,
                type=EventType.TOOL_CALL,
                name="email_sender",
                input={"to": "user@example.com"},
                output=None,
            )
        ]
        trace = _build_trace(events, tools_available=["search"])
        validator = ContractValidator(trace)

        violations = validator.get_violations()
        unknown_tools = [v for v in violations if v.violation_type == "unknown_tool"]

        assert len(unknown_tools) == 1
        assert unknown_tools[0].event_id == 42
        assert unknown_tools[0].tool_name == "email_sender"


class TestRootCauseBuilder:
    """Tests for root cause hypothesis building."""

    def _failure_trace(self) -> Trace:
        """Create a trace with multiple deterministic failure signals."""
        events = [
            TraceEvent(event_id=0, type=EventType.TOOL_CALL, name="search", input={"q": "x"}, output=None),
            TraceEvent(event_id=1, type=EventType.TOOL_CALL, name="search", input={"q": "x"}, output=None),
            TraceEvent(event_id=2, type=EventType.TOOL_CALL, name="search", input={"q": "x"}, output=None),
            TraceEvent(event_id=3, type=EventType.TOOL_CALL, name="nonexistent_tool", input={"q": "x"}, output=None),
            TraceEvent(event_id=4, type=EventType.ERROR, error=EventError(message="tool failed")),
            TraceEvent(event_id=6, type=EventType.ERROR, error=EventError(message="follow-on failure")),
        ]
        return _build_trace(
            events,
            tools_available=["search", "calculator"],
            status=TraceStatus.FAILED,
        )

    def test_build_preanalysis_bundle(self):
        """Build should return non-empty signals/hypotheses with a summary."""
        trace = self._failure_trace()
        bundle = RootCauseBuilder(trace).build()

        assert len(bundle.signals) >= 3
        assert len(bundle.hypotheses) > 0
        assert bundle.summary.strip() != ""

    def test_hypotheses_have_confidence(self):
        """Hypotheses should keep confidence and known category constraints."""
        trace = self._failure_trace()
        bundle = RootCauseBuilder(trace).build()

        allowed_categories = {"code", "prompt", "tool", "ops", "unknown"}
        for hypothesis in bundle.hypotheses:
            assert 0 <= hypothesis.confidence <= 1
            assert hypothesis.category in allowed_categories

    def test_to_dict(self):
        """Serialization should include core keys and non-empty suspects."""
        trace = self._failure_trace()
        bundle = RootCauseBuilder(trace).build()
        data = bundle.to_dict()

        assert "signals" in data
        assert "top_suspects" in data
        assert "summary" in data
        assert len(data["signals"]) > 0
        assert len(data["top_suspects"]) > 0
