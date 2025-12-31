"""
Generic JSON trace parser.

Fallback parser for trace formats that don't match specific parsers.
Attempts to extract common patterns from arbitrary JSON structures.
"""

from datetime import datetime
from typing import Any
import hashlib

from src.schema import (
    Trace,
    TraceEvent,
    TraceStatus,
    EventType,
    EventRole,
    EventError,
    TaskContext,
    EnvironmentInfo,
)
from src.ingestion.parser import TraceParser


class GenericJSONParser(TraceParser):
    """Fallback parser for generic JSON trace formats."""

    def can_parse(self, data: dict[str, Any]) -> bool:
        """Generic parser can always attempt to parse."""
        return isinstance(data, dict)

    def parse(self, data: dict[str, Any]) -> Trace:
        """Parse generic JSON into normalized format."""
        run_id = self._extract_run_id(data)
        timestamp_start, timestamp_end = self._extract_timestamps(data)
        status = self._extract_status(data)
        env = self._extract_environment(data)
        task = self._extract_task_context(data)
        events = self._extract_events(data)
        final_output = self._extract_final_output(data)
        error_summary = self._extract_error_summary(data, events)

        trace = Trace(
            run_id=run_id,
            trace_id=data.get("trace_id") or data.get("traceId"),
            timestamp_start=timestamp_start,
            timestamp_end=timestamp_end,
            status=status,
            task=task,
            env=env,
            events=events,
            final_output=final_output,
            error_summary=error_summary,
        )

        trace.stats = trace.calculate_stats()
        return trace

    def _extract_run_id(self, data: dict[str, Any]) -> str:
        """Extract or generate run ID."""
        for key in ["run_id", "runId", "id", "execution_id", "session_id", "thread_id"]:
            if key in data:
                return str(data[key])
        return hashlib.md5(str(data).encode()).hexdigest()[:12]

    def _extract_timestamps(
        self, data: dict[str, Any]
    ) -> tuple[datetime, datetime | None]:
        """Extract timestamps with flexible field names."""
        start_keys = ["start_time", "startTime", "timestamp", "created_at", "createdAt", "started_at"]
        end_keys = ["end_time", "endTime", "finished_at", "finishedAt", "completed_at", "completedAt"]

        start = None
        end = None

        for key in start_keys:
            if key in data:
                start = self._parse_timestamp(data[key])
                if start:
                    break

        for key in end_keys:
            if key in data:
                end = self._parse_timestamp(data[key])
                if end:
                    break

        if start is None:
            start = datetime.now()

        return start, end

    def _parse_timestamp(self, value: Any) -> datetime | None:
        """Parse various timestamp formats."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            # Handle both seconds and milliseconds
            if value > 1e12:  # milliseconds
                return datetime.fromtimestamp(value / 1000)
            return datetime.fromtimestamp(value)
        if isinstance(value, str):
            for fmt in [
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
            ]:
                try:
                    return datetime.strptime(value.replace("+00:00", "Z"), fmt)
                except ValueError:
                    continue
        return None

    def _extract_status(self, data: dict[str, Any]) -> TraceStatus:
        """Extract status with flexible detection."""
        for key in ["status", "state", "result"]:
            if key in data:
                status = str(data[key]).lower()
                if status in ["success", "completed", "done", "ok", "passed"]:
                    return TraceStatus.SUCCESS
                if status in ["failed", "error", "failure", "exception"]:
                    return TraceStatus.FAILED
                if status in ["timeout", "timed_out"]:
                    return TraceStatus.TIMEOUT
                if "loop" in status:
                    return TraceStatus.LOOP_DETECTED
                if status in ["cancelled", "canceled", "aborted", "interrupted"]:
                    return TraceStatus.CANCELLED

        # Check for error indicators
        if any(k in data for k in ["error", "exception", "errors"]):
            return TraceStatus.FAILED

        return TraceStatus.SUCCESS

    def _extract_environment(self, data: dict[str, Any]) -> EnvironmentInfo:
        """Extract environment info from various structures."""
        tools = []

        # Look for tools in common locations
        for key in ["tools", "functions", "available_tools", "tool_list"]:
            if key in data:
                tool_data = data[key]
                if isinstance(tool_data, list):
                    for t in tool_data:
                        if isinstance(t, str):
                            tools.append(t)
                        elif isinstance(t, dict):
                            tools.append(t.get("name", t.get("function", {}).get("name", str(t))))
                elif isinstance(tool_data, dict):
                    tools.extend(tool_data.keys())

        # Look for model
        model = None
        for key in ["model", "model_name", "modelName", "llm"]:
            if key in data:
                model = str(data[key])
                break

        # Try to detect framework
        framework = "unknown"
        data_str = str(data).lower()
        if "langgraph" in data_str:
            framework = "langgraph"
        elif "langchain" in data_str:
            framework = "langchain"
        elif "autogen" in data_str:
            framework = "autogen"
        elif "crewai" in data_str:
            framework = "crewai"

        return EnvironmentInfo(
            agent_framework=framework,
            model=model,
            tools_available=list(set(tools)),
        )

    def _extract_task_context(self, data: dict[str, Any]) -> TaskContext | None:
        """Extract task context from common patterns."""
        goal = None

        for key in ["goal", "task", "query", "prompt", "input", "question", "objective"]:
            if key in data:
                value = data[key]
                if isinstance(value, str):
                    goal = value
                elif isinstance(value, dict):
                    goal = value.get("text") or value.get("content") or value.get("goal")
                break

        if not goal:
            return None

        return TaskContext(
            goal=goal,
            success_criteria=data.get("success_criteria") or data.get("criteria"),
            expected_output_type=data.get("expected_output_type") or data.get("output_type"),
        )

    def _extract_events(self, data: dict[str, Any]) -> list[TraceEvent]:
        """Extract events from various structures."""
        events = []
        event_id = 0

        # Look for events in common locations
        raw_events = []
        for key in ["events", "steps", "messages", "logs", "history", "trace", "actions"]:
            if key in data and isinstance(data[key], list):
                raw_events = data[key]
                break

        for raw in raw_events:
            if not isinstance(raw, dict):
                # Handle string messages
                events.append(
                    TraceEvent(
                        event_id=event_id,
                        type=EventType.MESSAGE,
                        input=str(raw),
                    )
                )
                event_id += 1
                continue

            event_type = self._determine_event_type(raw)
            role = self._determine_role(raw)

            # Extract error if present
            error = None
            for error_key in ["error", "exception", "failure"]:
                if error_key in raw:
                    error_data = raw[error_key]
                    if isinstance(error_data, str):
                        error = EventError(message=error_data)
                    elif isinstance(error_data, dict):
                        error = EventError(
                            message=error_data.get("message", str(error_data)),
                            stack=error_data.get("stack") or error_data.get("traceback"),
                            category=error_data.get("type") or error_data.get("category"),
                        )
                    break

            event = TraceEvent(
                event_id=event_id,
                parent_event_id=raw.get("parent_id") or raw.get("parentId"),
                span_id=raw.get("span_id") or raw.get("spanId"),
                type=event_type,
                role=role,
                name=raw.get("name") or raw.get("tool") or raw.get("function") or raw.get("node"),
                input=raw.get("input") or raw.get("args") or raw.get("content") or raw.get("query"),
                output=raw.get("output") or raw.get("result") or raw.get("response"),
                token_count=raw.get("token_count") or raw.get("tokens") or raw.get("tokenCount"),
                latency_ms=raw.get("latency_ms") or raw.get("duration_ms") or raw.get("latency"),
                timestamp=self._parse_timestamp(raw.get("timestamp") or raw.get("time")),
                error=error,
                metadata=raw.get("metadata", {}),
            )
            events.append(event)
            event_id += 1

        return events

    def _determine_event_type(self, raw: dict[str, Any]) -> EventType:
        """Determine event type from raw data."""
        type_value = str(raw.get("type", "")).lower()

        type_mapping = {
            "llm": EventType.LLM_CALL,
            "model": EventType.LLM_CALL,
            "chat": EventType.LLM_CALL,
            "completion": EventType.LLM_CALL,
            "tool": EventType.TOOL_CALL,
            "function": EventType.TOOL_CALL,
            "action": EventType.TOOL_CALL,
            "decision": EventType.DECISION,
            "router": EventType.DECISION,
            "branch": EventType.DECISION,
            "error": EventType.ERROR,
            "exception": EventType.ERROR,
            "message": EventType.MESSAGE,
        }

        for key, event_type in type_mapping.items():
            if key in type_value:
                return event_type

        # Infer from content
        if any(k in raw for k in ["tool", "function", "action"]):
            return EventType.TOOL_CALL
        if any(k in raw for k in ["error", "exception"]):
            return EventType.ERROR
        if "model" in raw:
            return EventType.LLM_CALL

        return EventType.MESSAGE

    def _determine_role(self, raw: dict[str, Any]) -> EventRole | None:
        """Determine role from raw data."""
        role = str(raw.get("role", "")).lower()

        role_mapping = {
            "system": EventRole.SYSTEM,
            "user": EventRole.USER,
            "human": EventRole.USER,
            "assistant": EventRole.ASSISTANT,
            "ai": EventRole.ASSISTANT,
            "bot": EventRole.ASSISTANT,
            "tool": EventRole.TOOL,
            "function": EventRole.TOOL,
        }

        return role_mapping.get(role)

    def _extract_final_output(self, data: dict[str, Any]) -> str | dict | None:
        """Extract final output."""
        for key in ["output", "result", "response", "answer", "final_output"]:
            if key in data:
                return data[key]
        return None

    def _extract_error_summary(
        self, data: dict[str, Any], events: list[TraceEvent]
    ) -> str | None:
        """Extract error summary."""
        for key in ["error", "error_message", "exception"]:
            if key in data:
                error = data[key]
                if isinstance(error, str):
                    return error
                if isinstance(error, dict):
                    return error.get("message", str(error))

        # Collect from events
        errors = [e.error.message for e in events if e.error]
        if errors:
            return "; ".join(errors[:3])

        return None
