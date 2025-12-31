# Trace Ingestion

Agent Autopsy supports multiple trace formats with automatic detection.

## Format Detection

```mermaid
graph LR
    JSON[JSON Trace] --> Detect{Format Detection}
    
    Detect -->|thread_id<br/>checkpoint| LG[LangGraph]
    Detect -->|run_type<br/>callbacks| LC[LangChain]
    Detect -->|resourceSpans<br/>traceId| OT[OpenTelemetry]
    Detect -->|fallback| Gen[Generic]
    
    LG --> Parse[Parse]
    LC --> Parse
    OT --> Parse
    Gen --> Parse
    
    Parse --> Normalize[Normalize<br/>• Sequential IDs<br/>• Calculate stats<br/>• Validate]
    
    Normalize --> Schema[Trace Schema]
    
    classDef format fill:#fff9c4,stroke:#f57f17
    classDef process fill:#e1f5fe,stroke:#0277bd
    classDef output fill:#e8f5e9,stroke:#2e7d32
    
    class JSON,Detect format
    class LG,LC,OT,Gen,Parse,Normalize process
    class Schema output
```

## Supported Formats

1. **LangGraph**: Detects `thread_id`, `checkpoint`, or `runs` fields
2. **LangChain**: Detects `run_type` or `callbacks` fields
3. **OpenTelemetry**: Detects `resourceSpans` or `traceId` fields
4. **Generic**: Fallback for any JSON structure

## Normalization

- Ensures sequential event IDs
- Calculates statistics (tokens, latency, counts)
- Validates structure and references
- Fills missing timestamps

