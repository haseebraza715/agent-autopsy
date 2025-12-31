# Pattern Detection

Agent Autopsy automatically detects common failure patterns in agent traces.

## Pattern Types

```mermaid
graph TB
    Trace[Trace Events] --> Detector[Pattern Detector]
    
    Detector --> Loop[Infinite Loop<br/>CRITICAL<br/>Same tool+input 3+]
    Detector --> Retry[Retry Storm<br/>HIGH<br/>Same tool, varying input]
    Detector --> Cascade[Error Cascade<br/>HIGH<br/>Sequential errors]
    Detector --> Hallucination[Hallucinated Tool<br/>HIGH<br/>Tool not in list]
    Detector --> Empty[Empty Response<br/>MEDIUM<br/>Null/empty output]
    Detector --> Overflow[Context Overflow<br/>CRITICAL<br/>Token limit exceeded]
    
    Loop --> Signals[Signals]
    Retry --> Signals
    Cascade --> Signals
    Hallucination --> Signals
    Empty --> Signals
    Overflow --> Signals
    
    Signals --> Hypotheses[Root Cause Hypotheses]
    
    classDef critical fill:#ffebee,stroke:#d32f2f
    classDef high fill:#fff3e0,stroke:#f57c00
    classDef medium fill:#e3f2fd,stroke:#1976d2
    classDef output fill:#e8f5e9,stroke:#2e7d32
    
    class Loop,Overflow critical
    class Retry,Cascade,Hallucination high
    class Empty medium
    class Detector,Signals,Hypotheses output
```

## Detection Methods

- **Infinite Loop**: Tracks tool signatures (name + input hash)
- **Retry Storm**: Detects repeated tool calls with variations
- **Error Cascade**: Identifies sequential error events
- **Hallucinated Tool**: Validates against available tools list
- **Empty Response**: Checks for null/empty outputs
- **Context Overflow**: Compares token count to model limits

## Severity Levels

- **CRITICAL**: Infinite loops, context overflow
- **HIGH**: Retry storms, error cascades, hallucinated tools
- **MEDIUM**: Empty responses
- **LOW**: Minor issues

