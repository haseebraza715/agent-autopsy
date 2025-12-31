"""
Analysis tools for the LLM agent.

These tools allow the agent to query and explore trace data.
"""

from typing import Any, Callable

from src.schema import Trace, TraceEvent, EventType
from src.preanalysis import PatternDetector, RootCauseBuilder
from src.ingestion import TraceNormalizer


class AnalysisToolkit:
    """
    Provides tools for trace analysis.

    Each method is a tool that can be called by the LLM agent.
    """

    def __init__(self, trace: Trace):
        self.trace = trace
        self.pattern_detector = PatternDetector(trace)
        self.root_cause_builder = RootCauseBuilder(trace)
        self._preanalysis_bundle = None

    def get_trace_summary(self) -> dict[str, Any]:
        """
        Get an overview of the trace including stats and status.

        Returns:
            Dictionary with trace summary information
        """
        return TraceNormalizer.get_summary(self.trace)

    def get_event(self, event_id: int) -> dict[str, Any] | None:
        """
        Get a single event by its ID.

        Args:
            event_id: The ID of the event to retrieve

        Returns:
            Event data as dictionary, or None if not found
        """
        event = self.trace.get_event(event_id)
        if event is None:
            return None

        return {
            "event_id": event.event_id,
            "type": event.type.value,
            "role": event.role.value if event.role else None,
            "name": event.name,
            "input": event.input,
            "output": event.output,
            "token_count": event.token_count,
            "latency_ms": event.latency_ms,
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
            "error": {
                "message": event.error.message,
                "stack": event.error.stack,
                "category": event.error.category,
            } if event.error else None,
            "parent_event_id": event.parent_event_id,
            "metadata": event.metadata,
        }

    def get_events_range(self, start_id: int, end_id: int) -> list[dict[str, Any]]:
        """
        Get events within an ID range.

        Args:
            start_id: Start of range (inclusive)
            end_id: End of range (inclusive)

        Returns:
            List of events in the range
        """
        events = self.trace.get_events_in_range(start_id, end_id)
        return [self._event_to_dict(e) for e in events]

    def find_errors(self) -> list[dict[str, Any]]:
        """
        Find all error events in the trace.

        Returns:
            List of error events with details
        """
        error_events = self.trace.get_error_events()
        return [
            {
                "event_id": e.event_id,
                "type": e.type.value,
                "name": e.name,
                "error_message": e.error.message if e.error else "Error in event",
                "error_category": e.error.category if e.error else None,
            }
            for e in error_events
        ]

    def find_loops(self) -> list[dict[str, Any]]:
        """
        Find detected loop patterns in the trace.

        Returns:
            List of loop patterns with event IDs and details
        """
        patterns = self.pattern_detector.detect_loops()
        return [
            {
                "type": p.pattern_type.value,
                "severity": p.severity.value,
                "message": p.message,
                "evidence": p.evidence,
                "event_ids": p.event_ids,
            }
            for p in patterns
        ]

    def find_tool_calls(self, tool_name: str | None = None) -> list[dict[str, Any]]:
        """
        Find tool call events, optionally filtered by name.

        Args:
            tool_name: Optional tool name to filter by

        Returns:
            List of tool call events
        """
        tool_calls = self.trace.get_tool_calls()

        if tool_name:
            tool_calls = [t for t in tool_calls if t.name == tool_name]

        return [
            {
                "event_id": e.event_id,
                "name": e.name,
                "input": e.input,
                "output": e.output,
                "latency_ms": e.latency_ms,
                "has_error": e.is_error(),
            }
            for e in tool_calls
        ]

    def compare_events(self, event_id_1: int, event_id_2: int) -> dict[str, Any]:
        """
        Compare two events and show differences.

        Args:
            event_id_1: First event ID
            event_id_2: Second event ID

        Returns:
            Comparison result showing differences
        """
        event1 = self.trace.get_event(event_id_1)
        event2 = self.trace.get_event(event_id_2)

        if not event1 or not event2:
            return {"error": "One or both events not found"}

        result = {
            "event_1_id": event_id_1,
            "event_2_id": event_id_2,
            "same_type": event1.type == event2.type,
            "same_name": event1.name == event2.name,
            "same_input": event1.input == event2.input,
            "same_output": event1.output == event2.output,
            "differences": [],
        }

        if event1.type != event2.type:
            result["differences"].append(f"type: {event1.type.value} vs {event2.type.value}")
        if event1.name != event2.name:
            result["differences"].append(f"name: {event1.name} vs {event2.name}")
        if event1.input != event2.input:
            result["differences"].append("input differs")
        if event1.output != event2.output:
            result["differences"].append("output differs")

        return result

    def get_context_at_event(self, event_id: int, window: int = 3) -> dict[str, Any]:
        """
        Get the context (surrounding events) at a specific event.

        Args:
            event_id: The event to get context for
            window: Number of events before/after to include

        Returns:
            Context including previous events and accumulated state
        """
        event = self.trace.get_event(event_id)
        if not event:
            return {"error": "Event not found"}

        start = max(0, event_id - window)
        end = min(len(self.trace.events) - 1, event_id + window)

        context_events = self.trace.get_events_in_range(start, end)

        # Extract key information from context
        messages_before = []
        tools_called = []

        for e in context_events:
            if e.event_id < event_id:
                if e.type == EventType.MESSAGE:
                    messages_before.append({
                        "event_id": e.event_id,
                        "role": e.role.value if e.role else None,
                        "content_preview": str(e.input or e.output)[:200],
                    })
                elif e.type == EventType.TOOL_CALL:
                    tools_called.append({
                        "event_id": e.event_id,
                        "name": e.name,
                        "success": not e.is_error(),
                    })

        return {
            "event_id": event_id,
            "context_window": window,
            "events_in_context": len(context_events),
            "messages_before": messages_before,
            "tools_called_before": tools_called,
            "current_event": self._event_to_dict(event),
        }

    def get_contract_violations(self) -> list[dict[str, Any]]:
        """
        Get all contract violations from pre-analysis.

        Returns:
            List of contract violations with details
        """
        from src.preanalysis import ContractValidator
        validator = ContractValidator(self.trace)
        violations = validator.get_violations()

        return [
            {
                "event_id": v.event_id,
                "tool_name": v.tool_name,
                "violation_type": v.violation_type,
                "severity": v.severity.value,
                "message": v.message,
                "suggested_fix": v.suggested_fix,
            }
            for v in violations
        ]

    def get_preanalysis_bundle(self) -> dict[str, Any]:
        """
        Get the complete pre-analysis bundle with signals and hypotheses.

        Returns:
            Pre-analysis bundle with signals and top suspects
        """
        if self._preanalysis_bundle is None:
            self._preanalysis_bundle = self.root_cause_builder.build()
        return self._preanalysis_bundle.to_dict()

    def get_all_patterns(self) -> list[dict[str, Any]]:
        """
        Get all detected patterns (loops, errors, etc.).

        Returns:
            List of all detected patterns
        """
        patterns = self.pattern_detector.detect_all()
        return [
            {
                "type": p.pattern_type.value,
                "severity": p.severity.value,
                "message": p.message,
                "evidence": p.evidence,
                "event_ids": p.event_ids,
            }
            for p in patterns
        ]

    def _event_to_dict(self, event: TraceEvent) -> dict[str, Any]:
        """Convert an event to a dictionary."""
        return {
            "event_id": event.event_id,
            "type": event.type.value,
            "role": event.role.value if event.role else None,
            "name": event.name,
            "input": event.input,
            "output": event.output,
            "token_count": event.token_count,
            "latency_ms": event.latency_ms,
            "has_error": event.is_error(),
        }


def create_analysis_tools(trace: Trace) -> dict[str, Callable]:
    """
    Create a dictionary of analysis tools for the agent.

    Args:
        trace: The trace to analyze

    Returns:
        Dictionary mapping tool names to callable functions
    """
    toolkit = AnalysisToolkit(trace)

    return {
        "get_trace_summary": toolkit.get_trace_summary,
        "get_event": toolkit.get_event,
        "get_events_range": toolkit.get_events_range,
        "find_errors": toolkit.find_errors,
        "find_loops": toolkit.find_loops,
        "find_tool_calls": toolkit.find_tool_calls,
        "compare_events": toolkit.compare_events,
        "get_context_at_event": toolkit.get_context_at_event,
        "get_contract_violations": toolkit.get_contract_violations,
        "get_preanalysis_bundle": toolkit.get_preanalysis_bundle,
        "get_all_patterns": toolkit.get_all_patterns,
    }


# Tool definitions for LangGraph/LangChain
TOOL_DEFINITIONS = [
    {
        "name": "get_trace_summary",
        "description": "Get an overview of the trace including status, stats, and metadata.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_event",
        "description": "Get details of a single event by its ID.",
        "parameters": {
            "type": "object",
            "properties": {"event_id": {"type": "integer", "description": "The event ID to retrieve"}},
            "required": ["event_id"],
        },
    },
    {
        "name": "get_events_range",
        "description": "Get multiple events within an ID range.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_id": {"type": "integer", "description": "Start of range (inclusive)"},
                "end_id": {"type": "integer", "description": "End of range (inclusive)"},
            },
            "required": ["start_id", "end_id"],
        },
    },
    {
        "name": "find_errors",
        "description": "Find all error events in the trace.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "find_loops",
        "description": "Find detected loop patterns where the same operation is repeated.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "find_tool_calls",
        "description": "Find tool call events, optionally filtered by tool name.",
        "parameters": {
            "type": "object",
            "properties": {"tool_name": {"type": "string", "description": "Optional tool name filter"}},
            "required": [],
        },
    },
    {
        "name": "compare_events",
        "description": "Compare two events and show their differences.",
        "parameters": {
            "type": "object",
            "properties": {
                "event_id_1": {"type": "integer", "description": "First event ID"},
                "event_id_2": {"type": "integer", "description": "Second event ID"},
            },
            "required": ["event_id_1", "event_id_2"],
        },
    },
    {
        "name": "get_context_at_event",
        "description": "Get surrounding context (previous messages, tool calls) at a specific event.",
        "parameters": {
            "type": "object",
            "properties": {
                "event_id": {"type": "integer", "description": "The event to get context for"},
                "window": {"type": "integer", "description": "Number of events before/after", "default": 3},
            },
            "required": ["event_id"],
        },
    },
    {
        "name": "get_contract_violations",
        "description": "Get all contract violations (tool misuse, schema errors) from pre-analysis.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_preanalysis_bundle",
        "description": "Get the complete pre-analysis with signals and root cause hypotheses.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_all_patterns",
        "description": "Get all detected patterns (loops, cascades, overflows, etc.).",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
]
