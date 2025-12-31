# Pattern Detection

Agent Autopsy automatically detects common failure patterns in agent traces.

## Pattern Types

For detailed pattern detection flow, see [Pattern Detection Diagram](../diagrams/pattern_detection.mmd).

### Critical Severity

**Infinite Loop**
- **Description**: Same tool called with identical input 3+ times consecutively
- **Detection**: Tracks tool signatures (name + input hash)
- **Impact**: Agent stuck in endless loop, wasting resources

**Context Overflow**
- **Description**: Token count exceeds model's context window limit
- **Detection**: Compares cumulative token usage to model limits
- **Impact**: Agent cannot process full context, may fail or truncate

### High Severity

**Retry Storm**
- **Description**: Same tool called repeatedly with varying inputs
- **Detection**: Identifies repeated tool calls within short time window
- **Impact**: Inefficient execution, potential rate limiting

**Error Cascade**
- **Description**: Sequential errors propagating through execution
- **Detection**: Identifies chains of error events
- **Impact**: Multiple failures compounding, difficult to debug

**Hallucinated Tool**
- **Description**: Agent attempts to call tool not in available tools list
- **Detection**: Validates tool names against provided tools list
- **Impact**: Runtime errors, agent cannot complete task

### Medium Severity

**Empty Response**
- **Description**: LLM or tool returns null/empty output
- **Detection**: Checks for null, empty strings, or empty arrays
- **Impact**: Agent cannot proceed with empty data

## Detection Methods

- **Infinite Loop**: Tracks tool signatures (name + input hash) across consecutive events
- **Retry Storm**: Detects repeated tool calls with variations within time window
- **Error Cascade**: Identifies sequential error events with causal relationships
- **Hallucinated Tool**: Validates tool names against available tools list from environment
- **Empty Response**: Checks for null/empty outputs in LLM and tool responses
- **Context Overflow**: Compares cumulative token count to model's context window limit

## Severity Levels

- **CRITICAL**: Infinite loops, context overflow - immediate action required
- **HIGH**: Retry storms, error cascades, hallucinated tools - significant issues
- **MEDIUM**: Empty responses - moderate impact
- **LOW**: Minor issues - low priority

## Pattern Signals

Each detected pattern generates a signal containing:
- **Type**: Pattern type (loop, error, etc.)
- **Severity**: Critical, High, Medium, or Low
- **Evidence**: Description of what was detected
- **Event IDs**: Specific events involved in the pattern
- **Confidence**: Detection confidence score

