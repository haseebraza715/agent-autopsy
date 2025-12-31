# Output Generation

Agent Autopsy generates structured reports and actionable code artifacts.

## Output Flow

```mermaid
graph TB
    Result[Analysis Result] --> ReportGen[Report Generator]
    Signals[Signals] --> ArtifactGen[Artifact Generator]
    
    ReportGen --> Markdown[Markdown Report<br/>• Summary<br/>• Timeline<br/>• Root causes<br/>• Fix recommendations]
    ReportGen --> JSON[JSON Report<br/>Structured data]
    
    ArtifactGen --> PromptArt[Prompt Artifacts<br/>• Tool guardrails<br/>• Loop prevention]
    ArtifactGen --> CodeArt[Code Artifacts<br/>• Retry policies<br/>• Loop detection<br/>• Error handling]
    ArtifactGen --> ConfigArt[Config Artifacts<br/>• Timeouts<br/>• Retry settings]
    
    classDef report fill:#e0f2f1,stroke:#00695c
    classDef artifact fill:#f3e5f5,stroke:#7b1fa2
    
    class Result,Signals,ReportGen,ArtifactGen report
    class Markdown,JSON,PromptArt,CodeArt,ConfigArt artifact
```

## Report Structure

1. **Summary**: Status, confidence, brief description
2. **Timeline**: Key events from start to failure
3. **Root Cause Chain**: Step-by-step analysis with event citations
4. **Fix Recommendations**: 
   - A) Graph/Code fixes
   - B) Tool contract fixes
   - C) Prompt/policy fixes
   - D) Ops fixes
5. **Evidence**: Cited event IDs and supporting data

## Artifacts

Generated code patches include:
- **Prompt Updates**: System prompt additions
- **Code Snippets**: Retry logic, loop detection, error handling
- **Config Files**: Timeout and retry configurations

