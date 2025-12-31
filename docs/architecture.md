# Architecture Overview

Agent Autopsy analyzes agent execution traces to identify failures, loops, and issues.

## System Flow

```mermaid
graph TB
    User([User]) --> CLI[CLI]
    Config[Config] --> CLI
    
    CLI --> Parse[Parse Trace]
    Parse --> Format{Format Detection<br/>4 Formats}
    Format --> Parser[Parser]
    Parser --> Normalize[Normalize]
    
    Normalize --> Schema[Schema]
    Schema --> PreAnalysis[Pre-Analysis]
    
    PreAnalysis --> Patterns[Patterns]
    PreAnalysis --> Validator[Validator]
    PreAnalysis --> Builder[Root Cause Builder]
    
    Patterns --> Signals[Signals]
    Validator --> Signals
    Builder --> Signals
    
    Signals --> Decision{Analysis Mode}
    Decision -->|No LLM| Det[Deterministic]
    Decision -->|LLM| LLM[LLM Agent]
    
    LLM --> Tools[Analysis Tools]
    LLM --> API[OpenRouter]
    Tools --> LLM
    API --> LLM
    
    LLM --> Result[Result]
    Det --> Result
    
    Result --> Report[Report]
    Signals --> Artifacts[Artifacts]
    
    classDef entry fill:#e3f2fd,stroke:#1976d2
    classDef ingestion fill:#f3e5f5,stroke:#7b1fa2
    classDef analysis fill:#fce4ec,stroke:#c2185b
    classDef output fill:#e0f2f1,stroke:#00695c
    
    class User,CLI,Config entry
    class Parse,Format,Parser,Normalize,Schema ingestion
    class PreAnalysis,Patterns,Validator,Builder,Signals,Decision,LLM,Det,Tools,API,Result analysis
    class Report,Artifacts output
```

## Components

- **CLI**: Command-line interface for user interaction
- **Ingestion**: Parse and normalize traces from multiple formats
- **Pre-Analysis**: Pattern detection and contract validation
- **Analysis**: LLM-powered root cause analysis
- **Output**: Generate reports and code artifacts

