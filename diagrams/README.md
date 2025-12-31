# Diagrams

This directory contains architecture and workflow diagrams for Agent Autopsy.

## Diagram Files

### architecture.mmd / architecture.png
High-level architecture overview showing the main components and their relationships.

**Shows:**
- Input layer (User, Trace Files, Live Agents)
- Core system components (CLI, Ingestion, Pre-Analysis, Analysis, Output)
- External services (OpenRouter API)
- Output layer (Reports, Artifacts)

### system_flow.mmd
Complete system flow diagram showing the detailed analysis pipeline.

**Shows:**
- Trace input and format detection
- Ingestion pipeline with multiple parsers
- Pre-analysis components (Pattern Detector, Contract Validator, Root Cause Builder)
- Analysis mode decision (Deterministic vs LLM)
- LLM analysis path with tools and API
- Output generation (Reports and Artifacts)

### trace_generation.mmd
Workflow diagram for trace generation process.

**Shows:**
- Loading sample traces
- Running analysis agent with tracing enabled
- Event capture (LLM, Tool, Chain, Error events)
- Failure detection and recording
- Run control logic (min runs, stop on failure)

### pattern_detection.mmd
Pattern detection flow showing how different patterns are detected.

**Shows:**
- Pattern detector checks (Loop, Retry, Error, Tool, Output, Token)
- Pattern type classification (Critical, High, Medium)
- Signal generation
- Root cause hypothesis building
- Confidence scoring

## Generating PNG Files

To generate PNG files from Mermaid diagrams:

```bash
# Using Mermaid CLI
npm install -g @mermaid-js/mermaid-cli
mmdc -i architecture.mmd -o architecture.png

# Or use online tools
# https://mermaid.live/
```

## Diagram Conventions

**Colors:**
- Blue: Input/Entry points
- Purple: Processing/Ingestion
- Pink/Red: Analysis components
- Green: Output/Results
- Orange: Decisions/Conditions

**Shapes:**
- Rounded rectangles: Processes
- Diamonds: Decisions
- Cylinders: Data storage
- Circles: Start/End points

