"""
Pattern detection module.

Detects common agent failure patterns in traces:
- Infinite loops
- Retry storms
- Context overflow
- Hallucinated tools
- Empty responses
- Error cascades
- Goal drift
- Stale context
"""

from collections import Counter
from dataclasses import dataclass, field
from datetime import timedelta
from enum import Enum

from src.schema import Trace, TraceEvent, EventType
from src.utils.config import get_config


class PatternType(str, Enum):
    """Types of detectable patterns."""
    INFINITE_LOOP = "infinite_loop"
    RETRY_STORM = "retry_storm"
    CONTEXT_OVERFLOW = "context_overflow"
    HALLUCINATED_TOOL = "hallucinated_tool"
    EMPTY_RESPONSE = "empty_response"
    ERROR_CASCADE = "error_cascade"
    GOAL_DRIFT = "goal_drift"
    STALE_CONTEXT = "stale_context"
    TOOL_CONTRACT_MISMATCH = "tool_contract_mismatch"


class Severity(str, Enum):
    """Severity level of detected patterns."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class PatternResult:
    """Result of pattern detection."""
    pattern_type: PatternType
    severity: Severity
    message: str
    evidence: str
    event_ids: list[int] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class PatternDetector:
    """
    Detects common failure patterns in agent traces.

    All detection methods are deterministic and run before LLM analysis.
    """

    def __init__(self, trace: Trace):
        self.trace = trace

    def detect_all(self) -> list[PatternResult]:
        """Run all pattern detectors and return results."""
        results = []

        results.extend(self.detect_loops())
        results.extend(self.detect_retry_storms())
        results.extend(self.detect_empty_responses())
        results.extend(self.detect_error_cascades())
        results.extend(self.detect_hallucinated_tools())
        results.extend(self.detect_context_overflow())

        return results

    def detect_loops(self, threshold: int = 3) -> list[PatternResult]:
        """
        Detect infinite loops where the same tool+input is repeated consecutively.

        Args:
            threshold: Number of consecutive repetitions to trigger detection

        Returns:
            List of detected loop patterns
        """
        results = []
        tool_calls = self.trace.get_tool_calls()

        if len(tool_calls) < threshold:
            return results

        # Track consecutive sequences of identical tool signatures
        consecutive_count = 1
        last_sig = None
        sequence_start_id = None
        sequence_event_ids = []

        for event in tool_calls:
            sig = event.get_tool_signature()

            if sig == last_sig and sig is not None:
                # Continue the consecutive sequence
                consecutive_count += 1
                sequence_event_ids.append(event.event_id)
            else:
                # Check if previous sequence exceeded threshold
                if consecutive_count >= threshold and last_sig:
                    results.append(
                        PatternResult(
                            pattern_type=PatternType.INFINITE_LOOP,
                            severity=Severity.CRITICAL,
                            message=f"Identical tool call repeated {consecutive_count} times consecutively",
                            evidence=f"Same tool+input signature: {last_sig.split(':')[0]}",
                            event_ids=sequence_event_ids.copy(),
                            metadata={"signature": last_sig, "count": consecutive_count},
                        )
                    )

                # Start new sequence
                consecutive_count = 1
                sequence_event_ids = [event.event_id]

            last_sig = sig

        # Check final sequence
        if consecutive_count >= threshold and last_sig:
            results.append(
                PatternResult(
                    pattern_type=PatternType.INFINITE_LOOP,
                    severity=Severity.CRITICAL,
                    message=f"Identical tool call repeated {consecutive_count} times consecutively",
                    evidence=f"Same tool+input signature: {last_sig.split(':')[0]}",
                    event_ids=sequence_event_ids,
                    metadata={"signature": last_sig, "count": consecutive_count},
                )
            )

        return results

    def detect_retry_storms(self, threshold: int = 3) -> list[PatternResult]:
        """
        Detect retry storms where the same tool is called repeatedly within a time window.

        Uses configurable time window and checks for input similarity to distinguish
        retries from legitimate varied calls to the same tool.
        """
        results = []
        config = get_config()
        tool_calls = self.trace.get_tool_calls()

        if len(tool_calls) < threshold:
            return results

        window = timedelta(seconds=config.retry_window_seconds)

        # Group calls by tool name
        tool_events: dict[str, list[TraceEvent]] = {}
        for event in tool_calls:
            if event.name:
                if event.name not in tool_events:
                    tool_events[event.name] = []
                tool_events[event.name].append(event)

        # Check each tool for retry storms within time windows
        for tool_name, events in tool_events.items():
            if len(events) < threshold:
                continue

            # Find clusters of calls within time window
            i = 0
            while i < len(events):
                cluster = [events[i]]
                cluster_ids = [events[i].event_id]

                # Look for calls within window of first call in cluster
                for j in range(i + 1, len(events)):
                    # Check time proximity if timestamps available
                    if events[i].timestamp and events[j].timestamp:
                        delta = events[j].timestamp - events[i].timestamp
                        if delta <= window:
                            cluster.append(events[j])
                            cluster_ids.append(events[j].event_id)
                    else:
                        # No timestamps - use event ID proximity as fallback
                        if events[j].event_id - events[i].event_id <= 10:
                            cluster.append(events[j])
                            cluster_ids.append(events[j].event_id)

                if len(cluster) >= threshold:
                    # Check input similarity (are these actual retries?)
                    inputs = [str(e.input) for e in cluster]
                    unique_inputs = len(set(inputs))

                    # If inputs are similar (retries) or identical (loop)
                    # and this wasn't already caught as a loop
                    if unique_inputs <= len(cluster) // 2 + 1:
                        # Check not already detected as loop
                        loop_results = self.detect_loops()
                        is_loop = any(
                            set(cluster_ids) & set(r.event_ids)
                            for r in loop_results
                        )

                        if not is_loop:
                            results.append(
                                PatternResult(
                                    pattern_type=PatternType.RETRY_STORM,
                                    severity=Severity.HIGH,
                                    message=f"Tool '{tool_name}' called {len(cluster)} times within {config.retry_window_seconds}s",
                                    evidence=f"Multiple calls with similar inputs ({unique_inputs} unique inputs)",
                                    event_ids=cluster_ids,
                                    metadata={
                                        "tool_name": tool_name,
                                        "count": len(cluster),
                                        "unique_inputs": unique_inputs,
                                        "window_seconds": config.retry_window_seconds,
                                    },
                                )
                            )
                            # Skip past this cluster
                            i = i + len(cluster) - 1
                            break

                i += 1

        return results

    def detect_empty_responses(self) -> list[PatternResult]:
        """Detect events with empty or null outputs."""
        results = []
        empty_events = []

        for event in self.trace.events:
            if event.type in [EventType.LLM_CALL, EventType.TOOL_CALL]:
                output = event.output
                is_empty = (
                    output is None
                    or output == ""
                    or (isinstance(output, str) and output.strip() == "")
                    or output == {}
                    or output == []
                )

                if is_empty:
                    empty_events.append(event.event_id)

        if empty_events:
            results.append(
                PatternResult(
                    pattern_type=PatternType.EMPTY_RESPONSE,
                    severity=Severity.MEDIUM,
                    message=f"Found {len(empty_events)} events with empty outputs",
                    evidence="Empty or null output detected",
                    event_ids=empty_events,
                )
            )

        return results

    def detect_error_cascades(self) -> list[PatternResult]:
        """Detect sequences of errors that propagate through the trace."""
        results = []
        error_events = self.trace.get_error_events()

        if len(error_events) < 2:
            return results

        # Look for consecutive or closely grouped errors
        error_ids = [e.event_id for e in error_events]
        cascades = []
        current_cascade = [error_ids[0]]

        for i in range(1, len(error_ids)):
            # If errors are within 3 events of each other, consider it a cascade
            if error_ids[i] - error_ids[i - 1] <= 3:
                current_cascade.append(error_ids[i])
            else:
                if len(current_cascade) >= 2:
                    cascades.append(current_cascade)
                current_cascade = [error_ids[i]]

        if len(current_cascade) >= 2:
            cascades.append(current_cascade)

        for cascade in cascades:
            results.append(
                PatternResult(
                    pattern_type=PatternType.ERROR_CASCADE,
                    severity=Severity.HIGH,
                    message=f"Error cascade: {len(cascade)} consecutive errors",
                    evidence="Errors propagating sequentially across events",
                    event_ids=cascade,
                    metadata={"cascade_length": len(cascade)},
                )
            )

        return results

    def detect_hallucinated_tools(self) -> list[PatternResult]:
        """Detect tool calls to tools not in the available tools list."""
        results = []
        available_tools = set(self.trace.env.tools_available)

        if not available_tools:
            # Can't detect if we don't know what tools are available
            return results

        hallucinated = []

        for event in self.trace.get_tool_calls():
            if event.name and event.name not in available_tools:
                hallucinated.append(event.event_id)

        if hallucinated:
            results.append(
                PatternResult(
                    pattern_type=PatternType.HALLUCINATED_TOOL,
                    severity=Severity.HIGH,
                    message=f"Found {len(hallucinated)} calls to unknown tools",
                    evidence=f"Tool called not in available tools: {available_tools}",
                    event_ids=hallucinated,
                    metadata={"available_tools": list(available_tools)},
                )
            )

        return results

    def detect_context_overflow(self, threshold: int | None = None) -> list[PatternResult]:
        """
        Detect potential context overflow based on token counts.

        Uses configurable threshold from Config, with optional override.
        Also considers model-specific context limits when available.
        """
        results = []
        config = get_config()
        total_tokens = self.trace.stats.total_tokens or 0

        # Use config threshold if not overridden
        if threshold is None:
            threshold = config.context_overflow_threshold

        # Check for model-specific limits and use the more restrictive
        model = self.trace.env.model
        if model:
            # Common model context limits
            model_limits = {
                "gpt-4": 128000,
                "gpt-4-turbo": 128000,
                "gpt-4o": 128000,
                "gpt-3.5-turbo": 16000,
                "gpt-3.5-turbo-16k": 16000,
                "claude-3": 200000,
                "claude-3-opus": 200000,
                "claude-3-sonnet": 200000,
                "claude-3-haiku": 200000,
                "claude-2": 100000,
                "llama-3": 8000,
                "llama-3.1": 128000,
                "mistral": 32000,
            }
            # Find matching model limit (partial match)
            model_lower = model.lower()
            for model_name, limit in model_limits.items():
                if model_name in model_lower:
                    threshold = min(threshold, limit)
                    break

        if total_tokens >= threshold:
            # Find which events contributed most to token usage
            token_events = [
                (e.event_id, e.token_count)
                for e in self.trace.events
                if e.token_count and e.token_count > 0
            ]
            token_events.sort(key=lambda x: x[1], reverse=True)
            top_events = [e[0] for e in token_events[:5]]

            results.append(
                PatternResult(
                    pattern_type=PatternType.CONTEXT_OVERFLOW,
                    severity=Severity.CRITICAL,
                    message=f"Token count ({total_tokens}) approaching/exceeding limit",
                    evidence=f"Total tokens: {total_tokens}, threshold: {threshold}" +
                             (f" (model: {model})" if model else ""),
                    event_ids=top_events,
                    metadata={
                        "total_tokens": total_tokens,
                        "threshold": threshold,
                        "model": model,
                    },
                )
            )

        return results

    def find_errors(self) -> list[TraceEvent]:
        """Get all error events from the trace."""
        return self.trace.get_error_events()

    def find_loops(self) -> list[PatternResult]:
        """Alias for detect_loops for tool compatibility."""
        return self.detect_loops()
