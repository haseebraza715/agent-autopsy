# Architecture Overview

Agent Autopsy analyzes agent execution traces to identify failures, loops, and issues.

## High-Level Architecture

![Architecture](diagrams/architecture.png)

## System Flow

For detailed system flow, see [System Flow Diagram](../diagrams/system_flow.mmd).

## Components

### Input Layer
- **CLI Interface**: Command-line interface for user interaction
- **Trace Files**: Pre-recorded trace files in various formats
- **Live Agents**: Real-time trace capture from running agents

### Core System

#### Ingestion Layer
- **Format Detection**: Detects trace format (LangGraph, LangChain, OpenTelemetry, Generic JSON)
- **Parsers**: Dedicated parser for LangGraph plus a generic fallback (LangChain/OpenTelemetry currently parsed generically)
- **Normalization**: Converts all formats to unified schema

#### Pre-Analysis Engine
- **Pattern Detector**: Identifies common failure patterns (loops, errors, etc.)
- **Contract Validator**: Validates tool contracts and schemas
- **Root Cause Builder**: Generates hypotheses with confidence scores

#### Analysis Engine
- **Deterministic Analysis**: Pattern-based analysis without LLM
- **LLM Analysis**: AI-powered root cause analysis using ReAct agent
- **Analysis Tools**: Tools for querying trace data during LLM analysis

#### Output Layer
- **Report Generator**: Creates structured markdown/JSON reports
- **Artifact Generator**: Generates code patches and fix recommendations

### External Services
- **OpenRouter API**: LLM provider for analysis

## Data Flow

1. **Input**: Trace file or live agent execution
2. **Ingestion**: Parse and normalize to unified schema
3. **Pre-Analysis**: Detect patterns and generate signals
4. **Analysis**: Run deterministic or LLM-based analysis
5. **Output**: Generate reports and artifacts

## Related Diagrams

- [System Flow](../diagrams/system_flow.mmd) - Complete analysis pipeline
- [Trace Generation](../diagrams/trace_generation.mmd) - Trace generation workflow
- [Pattern Detection](../diagrams/pattern_detection.mmd) - Pattern detection flow
