"""Tests for the schema module."""

import re
import subprocess
import sys
from datetime import datetime

from agent_autopsy.schema import (
    EnvironmentInfo,
    EventError,
    EventRole,
    EventType,
    TaskContext,
    Trace,
    TraceEvent,
    TraceStatus,
)


class TestTraceEvent:
    """Tests for TraceEvent model."""

    def test_create_basic_event(self):
        """Test creating a basic event."""
        event = TraceEvent(
            event_id=0,
            type=EventType.MESSAGE,
            input="Hello",
        )
        assert event.event_id == 0
        assert event.type == EventType.MESSAGE
        assert event.input == "Hello"
        assert event.output is None
        assert event.error is None

    def test_create_tool_call_event(self):
        """Test creating a tool call event."""
        event = TraceEvent(
            event_id=1,
            type=EventType.TOOL_CALL,
            role=EventRole.TOOL,
            name="calculator",
            input={"expression": "2 + 2"},
            output={"result": 4},
            latency_ms=50,
        )
        assert event.type == EventType.TOOL_CALL
        assert event.name == "calculator"
        assert event.latency_ms == 50

    def test_event_is_error(self):
        """Test error detection in events."""
        normal_event = TraceEvent(event_id=0, type=EventType.MESSAGE)
        assert not normal_event.is_error()

        error_event = TraceEvent(
            event_id=1,
            type=EventType.ERROR,
            error=EventError(message="Something failed"),
        )
        assert error_event.is_error()

        event_with_error = TraceEvent(
            event_id=2,
            type=EventType.TOOL_CALL,
            error=EventError(message="Tool failed"),
        )
        assert event_with_error.is_error()

    def test_get_tool_signature(self):
        """Test tool signature generation."""
        event = TraceEvent(
            event_id=0,
            type=EventType.TOOL_CALL,
            name="search",
            input={"query": "test"},
        )
        sig = event.get_tool_signature()
        assert sig is not None
        assert sig.startswith("search:")

        # Non-tool events should return None
        message_event = TraceEvent(event_id=1, type=EventType.MESSAGE)
        assert message_event.get_tool_signature() is None

    def test_get_tool_signature_is_stable_and_key_order_independent(self):
        """Signatures must not depend on dict insertion order or process salt."""
        event_a = TraceEvent(
            event_id=0,
            type=EventType.TOOL_CALL,
            name="search",
            input={"query": "test", "limit": 5},
        )
        event_b = TraceEvent(
            event_id=1,
            type=EventType.TOOL_CALL,
            name="search",
            input={"limit": 5, "query": "test"},
        )
        assert event_a.get_tool_signature() == event_b.get_tool_signature()
        assert re.fullmatch(r"search:[0-9a-f]{16}", event_a.get_tool_signature() or "")
        # Never a Python hash() integer (process-salted, non-reproducible).
        assert "-" not in (event_a.get_tool_signature() or "")

    def test_get_tool_signature_is_stable_across_processes(self):
        """Cross-process determinism: the signature value must be identical in
        separate interpreters (Python's builtin hash() is salted per-process)."""

        code = (
            "from agent_autopsy.schema import EventType, TraceEvent;"
            "e = TraceEvent(event_id=0, type=EventType.TOOL_CALL,"
            " name='search', input={'query': 'test'});"
            "print(e.get_tool_signature())"
        )
        out1 = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60)
        out2 = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60)
        assert out1.returncode == out2.returncode == 0
        assert out1.stdout.strip() == out2.stdout.strip()
        assert re.fullmatch(r"search:[0-9a-f]{16}", out1.stdout.strip())


class TestTrace:
    """Tests for Trace model."""

    def test_create_minimal_trace(self):
        """Test creating a minimal trace."""
        trace = Trace(
            run_id="test-001",
            timestamp_start=datetime.now(),
            status=TraceStatus.SUCCESS,
            env=EnvironmentInfo(agent_framework="test"),
        )
        assert trace.run_id == "test-001"
        assert trace.status == TraceStatus.SUCCESS
        assert len(trace.events) == 0

    def test_create_trace_with_events(self):
        """Test creating a trace with events."""
        events = [
            TraceEvent(event_id=0, type=EventType.MESSAGE, role=EventRole.USER),
            TraceEvent(event_id=1, type=EventType.LLM_CALL, name="gpt-4"),
            TraceEvent(event_id=2, type=EventType.TOOL_CALL, name="search"),
        ]

        trace = Trace(
            run_id="test-002",
            timestamp_start=datetime.now(),
            status=TraceStatus.SUCCESS,
            env=EnvironmentInfo(agent_framework="langgraph"),
            events=events,
        )

        assert len(trace.events) == 3
        assert trace.get_event(1).name == "gpt-4"

    def test_get_events_by_type(self):
        """Test filtering events by type."""
        events = [
            TraceEvent(event_id=0, type=EventType.MESSAGE),
            TraceEvent(event_id=1, type=EventType.LLM_CALL),
            TraceEvent(event_id=2, type=EventType.TOOL_CALL),
            TraceEvent(event_id=3, type=EventType.TOOL_CALL),
        ]

        trace = Trace(
            run_id="test-003",
            timestamp_start=datetime.now(),
            status=TraceStatus.SUCCESS,
            env=EnvironmentInfo(agent_framework="test"),
            events=events,
        )

        tool_calls = trace.get_tool_calls()
        assert len(tool_calls) == 2

        llm_calls = trace.get_llm_calls()
        assert len(llm_calls) == 1

    def test_calculate_stats(self):
        """Test stats calculation."""
        events = [
            TraceEvent(event_id=0, type=EventType.LLM_CALL, token_count=100),
            TraceEvent(event_id=1, type=EventType.LLM_CALL, token_count=150),
            TraceEvent(event_id=2, type=EventType.TOOL_CALL, latency_ms=50),
            TraceEvent(event_id=3, type=EventType.ERROR, error=EventError(message="err")),
        ]

        trace = Trace(
            run_id="test-004",
            timestamp_start=datetime.now(),
            status=TraceStatus.FAILED,
            env=EnvironmentInfo(agent_framework="test"),
            events=events,
        )

        stats = trace.calculate_stats()
        assert stats.num_llm_calls == 2
        assert stats.num_tool_calls == 1
        assert stats.num_errors == 1
        assert stats.total_tokens == 250
        assert stats.total_latency_ms == 50

    def test_agent_helpers(self):
        """Agent helper methods should expose IDs, events, and handoffs."""
        events = [
            TraceEvent(event_id=0, type=EventType.MESSAGE, agent_id="planner"),
            TraceEvent(event_id=1, type=EventType.TOOL_CALL, agent_id="planner", name="search"),
            TraceEvent(event_id=2, type=EventType.ERROR, agent_id="executor", error=EventError(message="boom")),
            TraceEvent(event_id=3, type=EventType.MESSAGE, agent_id="reviewer"),
        ]
        trace = Trace(
            run_id="test-agents-001",
            timestamp_start=datetime.now(),
            status=TraceStatus.FAILED,
            env=EnvironmentInfo(agent_framework="multi"),
            events=events,
        )

        assert trace.get_agent_ids() == ["executor", "planner", "reviewer"]
        assert [e.event_id for e in trace.get_events_by_agent("planner")] == [0, 1]
        assert trace.get_agent_handoffs() == [(2, "planner", "executor"), (3, "executor", "reviewer")]


class TestTaskContext:
    """Tests for TaskContext model."""

    def test_create_task_context(self):
        """Test creating task context."""
        task = TaskContext(
            goal="Find the weather",
            success_criteria=["Must include temperature", "Must include humidity"],
            expected_output_type="json",
        )
        assert task.goal == "Find the weather"
        assert len(task.success_criteria) == 2


class TestEnvironmentInfo:
    """Tests for EnvironmentInfo model."""

    def test_create_environment_info(self):
        """Test creating environment info."""
        env = EnvironmentInfo(
            agent_framework="langgraph",
            model="gpt-4",
            tools_available=["search", "calculator"],
        )
        assert env.agent_framework == "langgraph"
        assert len(env.tools_available) == 2
