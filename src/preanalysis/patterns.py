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
from enum import Enum

from src.schema import Trace, TraceEvent, EventType


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
        Detect infinite loops where the same tool+input is repeated.

        Args:
            threshold: Number of repetitions to trigger detection

        Returns:
            List of detected loop patterns
        """
        results = []
        tool_calls = self.trace.get_tool_calls()

        if len(tool_calls) < threshold:
            return results

        # Track tool signatures (name + input hash)
        signatures: dict[str, list[int]] = {}

        for event in tool_calls:
            sig = event.get_tool_signature()
            if sig:
                if sig not in signatures:
                    signatures[sig] = []
                signatures[sig].append(event.event_id)

        # Find repeated signatures
        for sig, event_ids in signatures.items():
            if len(event_ids) >= threshold:
                results.append(
                    PatternResult(
                        pattern_type=PatternType.INFINITE_LOOP,
                        severity=Severity.CRITICAL,
                        message=f"Identical tool call repeated {len(event_ids)} times",
                        evidence=f"Same tool+input signature: {sig.split(':')[0]}",
                        event_ids=event_ids,
                        metadata={"signature": sig, "count": len(event_ids)},
                    )
                )

        return results

    def detect_retry_storms(self, threshold: int = 3) -> list[PatternResult]:
        """
        Detect retry storms where the same tool is called repeatedly with similar inputs.

        More lenient than loop detection - looks for same tool name with varying inputs.
        """
        results = []
        tool_calls = self.trace.get_tool_calls()

        if len(tool_calls) < threshold:
            return results

        # Count calls per tool
        tool_counts: dict[str, list[int]] = {}

        for event in tool_calls:
            if event.name:
                if event.name not in tool_counts:
                    tool_counts[event.name] = []
                tool_counts[event.name].append(event.event_id)

        # Find tools with many calls
        for tool_name, event_ids in tool_counts.items():
            if len(event_ids) >= threshold:
                # Check if it's not already detected as a loop
                loop_detected = any(
                    tool_name in (r.metadata.get("signature", "") or "")
                    for r in self.detect_loops()
                )

                if not loop_detected:
                    results.append(
                        PatternResult(
                            pattern_type=PatternType.RETRY_STORM,
                            severity=Severity.HIGH,
                            message=f"Tool '{tool_name}' called {len(event_ids)} times",
                            evidence=f"Multiple calls to same tool with varying inputs",
                            event_ids=event_ids,
                            metadata={"tool_name": tool_name, "count": len(event_ids)},
                        )
                    )

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

    def detect_context_overflow(self, threshold: int = 100000) -> list[PatternResult]:
        """
        Detect potential context overflow based on token counts.

        Args:
            threshold: Token threshold to trigger detection (default 100k)
        """
        results = []
        total_tokens = self.trace.stats.total_tokens or 0

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
                    evidence=f"Total tokens: {total_tokens}, threshold: {threshold}",
                    event_ids=top_events,
                    metadata={
                        "total_tokens": total_tokens,
                        "threshold": threshold,
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
