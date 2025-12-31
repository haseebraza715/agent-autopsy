# Analysis Pipeline

Agent Autopsy uses deterministic pattern detection combined with LLM reasoning.

## Analysis Flow

```mermaid
graph TB
    Trace[Trace] --> PreAnalysis[Pre-Analysis]
    
    PreAnalysis --> Patterns[Pattern Detection<br/>• Loops<br/>• Errors<br/>• Hallucinations]
    PreAnalysis --> Contracts[Contract Validation<br/>• Schema check<br/>• Type validation]
    PreAnalysis --> Builder[Root Cause Builder<br/>• Hypotheses<br/>• Confidence scores]
    
    Patterns --> Signals[Signals]
    Contracts --> Signals
    Builder --> Signals
    
    Signals --> Decision{Analysis Mode}
    
    Decision -->|--no-llm| Det[Deterministic<br/>Pattern-based only]
    Decision -->|With API Key| LLM[LLM Analysis<br/>ReAct Agent]
    
    LLM --> Tools[Analysis Tools<br/>get_event, find_errors, etc.]
    LLM --> API[OpenRouter API]
    Tools --> LLM
    API --> LLM
    
    LLM --> Result[Analysis Result]
    Det --> Result
    
    Result --> Report[Report]
    
    classDef pre fill:#fff3e0,stroke:#ef6c00
    classDef analysis fill:#fce4ec,stroke:#c2185b
    classDef output fill:#e0f2f1,stroke:#00695c
    
    class Trace,PreAnalysis,Patterns,Contracts,Builder,Signals pre
    class Decision,Det,LLM,Tools,API,Result analysis
    class Report output
```

## Pattern Detection

Detects common failure patterns:
- **Infinite Loops**: Same tool+input repeated 3+ times
- **Retry Storms**: Same tool with varying inputs
- **Error Cascades**: Sequential errors propagating
- **Hallucinated Tools**: Tools not in available list
- **Empty Responses**: Null/empty outputs
- **Context Overflow**: Token limits exceeded

## LLM Analysis

Uses LangGraph ReAct agent with:
- **Analysis Tools**: Query trace data
- **OpenRouter API**: LLM provider
- **Event Citations**: References specific events
- **Root Cause Chain**: Step-by-step analysis

