# Output Generation

Agent Autopsy generates structured reports and actionable code artifacts to help fix identified issues.

## Output Types

### Reports

**Markdown Reports** (default)
- Human-readable format
- Structured sections with clear hierarchy
- Event citations and evidence
- Suitable for documentation and sharing

**JSON Reports**
- Machine-readable format
- Structured data for programmatic processing
- Complete analysis data
- Suitable for integration with other tools

### Artifacts

**Code Artifacts**
- Retry policies for failed operations
- Loop detection and prevention code
- Error handling improvements
- Guard clauses and validation

**Prompt Artifacts**
- System prompt additions
- Tool guardrails and restrictions
- Loop prevention instructions
- Error recovery guidance

**Config Artifacts**
- Timeout configurations
- Retry settings
- Rate limiting parameters
- Monitoring configurations

## Report Structure

### 1. Summary
- Execution status (success/failed/timeout)
- Confidence level (0-1 scale)
- Brief description of the issue
- Key metrics (events, errors, duration)

### 2. Timeline
- Chronological list of key events
- Event IDs and types
- Transitions between states
- Failure point identification

### 3. Root Cause Chain
- Step-by-step analysis
- Event citations for each step
- Causal relationships
- Supporting evidence

### 4. Fix Recommendations

Categorized by implementation type:

**A) Graph/Code Fixes**
- Changes to agent graph structure
- Routing logic modifications
- State management improvements
- Node/edge additions or removals

**B) Tool Contract Fixes**
- Schema validation updates
- Input/output checking
- Error handling in tools
- Contract enforcement

**C) Prompt/Policy Fixes**
- System prompt changes
- Behavioral guardrails
- Tool usage policies
- Error recovery instructions

**D) Ops Fixes**
- Timeout configurations
- Retry policies
- Caching strategies
- Monitoring and alerting

### 5. Evidence
- Cited event IDs
- Supporting trace data
- Pattern detection results
- Confidence scores

## Artifact Generation

Artifacts are generated based on detected patterns and signals:

**For Infinite Loops:**
- Loop detection code
- Max iteration guards
- State tracking mechanisms

**For Retry Storms:**
- Exponential backoff policies
- Rate limiting code
- Circuit breaker patterns

**For Error Cascades:**
- Error handling improvements
- Fallback mechanisms
- Error recovery strategies

**For Hallucinated Tools:**
- Tool validation code
- Available tools checking
- Tool whitelist enforcement

**For Context Overflow:**
- Token counting utilities
- Context window management
- Truncation strategies

## Output Formats

### Markdown Report Example

```markdown
# Autopsy Report: Run abc123

## Summary
- Status: failed
- Confidence: 0.85
- Issue: Infinite loop detected in tool calls

## Timeline
- Event 0: llm_start
- Event 1: tool_start (calculator)
- Event 2: tool_end (calculator)
- Event 3: tool_start (calculator) [LOOP DETECTED]

## Root Cause Chain
1. Event 1: Tool called with input X
2. Event 3: Same tool called with identical input X
3. Event 5: Pattern repeats, indicating missing exit condition

## Fix Recommendations
A) Graph/Code Fixes:
- Add max_iterations check in router logic
- Implement state tracking for tool calls

## Evidence
- Events 1, 3, 5: Same tool+input signature
- Pattern: Infinite Loop (CRITICAL)
```

### JSON Report Structure

```json
{
  "run_id": "abc123",
  "status": "failed",
  "confidence": 0.85,
  "summary": "...",
  "timeline": [...],
  "root_cause_chain": [...],
  "fix_recommendations": {
    "code": [...],
    "tool": [...],
    "prompt": [...],
    "ops": [...]
  },
  "evidence": {
    "event_ids": [1, 3, 5],
    "patterns": [...]
  }
}
```

## Batch Analysis Reports

When analyzing multiple traces (using `scripts/analyze_traces.py`), a summary report is generated:

- Overview statistics
- Pattern detection summary
- Severity distribution
- Error type breakdown
- Individual trace results table
- Detailed pattern analysis grouped by type

See [Scripts](../scripts/README.md) for more information on batch analysis.

