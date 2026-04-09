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

**Goal Drift**
- **Description**: Agent behavior diverges from the original task objective
- **Detection**: Compares early vs late lexical overlap with task goal
- **Impact**: Agent may complete irrelevant work

**Stale Context**
- **Description**: Agent repeats calls using outdated assumptions
- **Detection**: Identifies same tool+input producing changed outputs across retries
- **Impact**: Slow recovery and repeated wrong actions

**Token Waste**
- **Description**: High token spend with low useful transition ratio
- **Detection**: Compares LLM token usage against nearby useful transitions
- **Impact**: Increased cost and latency with limited progress

**Redundant Tool Calls**
- **Description**: Same tool+input invoked repeatedly at different points
- **Detection**: Detects identical non-consecutive tool signatures
- **Impact**: Duplicate work and wasted latency budget

### High Severity (Additional)

**Permission/Auth Failures**
- **Description**: Repeated authentication/authorization failures
- **Detection**: Matches auth-related failure signatures in event text
- **Impact**: Agent remains blocked until credentials/scopes are corrected

**Timeout Patterns**
- **Description**: Timeout errors or slow-call bottlenecks dominate execution
- **Detection**: Combines timeout-signature matching with latency threshold checks
- **Impact**: Latency-driven failures and unstable execution

## Detection Methods

- **Infinite Loop**: Tracks tool signatures (name + input hash) across consecutive events
- **Retry Storm**: Detects repeated tool calls with variations within time window
- **Error Cascade**: Identifies sequential error events with causal relationships
- **Hallucinated Tool**: Validates tool names against available tools list from environment
- **Empty Response**: Checks for null/empty outputs in LLM and tool responses
- **Context Overflow**: Compares cumulative token count to model's context window limit
- **Goal Drift**: Measures drop in task-goal similarity across execution windows
- **Stale Context**: Detects changed outputs for repeated identical calls
- **Token Waste**: Evaluates useful-token ratio from event transitions
- **Permission/Auth Failures**: Detects repeated auth signature failures
- **Timeout Patterns**: Correlates timeout messages and slow latency events
- **Redundant Tool Calls**: Detects identical non-consecutive tool call signatures

## Severity Levels

- **CRITICAL**: Infinite loops, context overflow - immediate action required
- **HIGH**: Retry storms, error cascades, hallucinated tools - significant issues
- **MEDIUM**: Empty responses - moderate impact
- **MEDIUM**: Goal drift, stale context, token waste, redundant calls
- **LOW**: Minor issues - low priority

## Pattern Signals

Each detected pattern generates a signal containing:
- **Type**: Pattern type (loop, error, etc.)
- **Severity**: Critical, High, Medium, or Low
- **Evidence**: Description of what was detected
- **Event IDs**: Specific events involved in the pattern
- **Confidence**: Detection confidence score
