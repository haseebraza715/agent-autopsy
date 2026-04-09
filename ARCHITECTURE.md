# Architecture

Agent Autopsy analyzes agent traces through a modular pipeline: ingest traces, detect deterministic failures, optionally run LLM synthesis, then output reports and fixes.

## System Diagram

```mermaid
flowchart LR
    A[Inputs: CLI, Streamlit, MCP, Trace Files] --> B[Ingestion]
    B --> B1[Format Detection]
    B --> B2[Parsers: LangGraph/LangChain/OTel/Generic/Plugins]
    B --> C[Normalization to Trace Schema]

    C --> D[Pre-Analysis]
    D --> D1[Pattern Detection]
    D --> D2[Contract Validation]
    D --> D3[Root Cause Hypotheses]

    D --> E{Analysis Mode}
    E -->|Deterministic| F[Deterministic Report]
    E -->|LLM Enabled| G[LLM Analysis Agent]
    G --> H[Report Synthesis]

    F --> I[Outputs]
    H --> I

    I --> I1[Markdown/JSON Reports]
    I --> I2[Fix Suggestions & Artifacts]
    I --> I3[MCP Tool Responses]
```

## Notes

- Core execution path is deterministic-first; LLM analysis is optional and has fallback behavior.
- Advanced features include trace comparison, benchmark aggregation, and live monitoring alerts.
- Extensions are supported via plugin interfaces for parsers, detectors, reports, fix generation, and visualizations.

For detailed component descriptions, see [docs/architecture.md](docs/architecture.md).
