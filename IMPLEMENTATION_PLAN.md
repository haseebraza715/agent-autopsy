# Agent Autopsy - Implementation Plan

## Overview

This document outlines the step-by-step implementation plan for building the Agent Autopsy system - a tool for analyzing and debugging agent traces to identify failures, loops, and other issues.

---

## Phase 1: Foundation & MVP (Priority: Highest)

### 1.1 Project Setup
- [ ] Initialize Python project with `pyproject.toml` or `requirements.txt`
- [ ] Set up virtual environment
- [ ] Create base directory structure
- [ ] Configure `.env.example` with required environment variables
- [ ] Set up basic logging configuration

### 1.2 Schema Layer (`src/schema/`)
- [ ] Define `TraceSchemaV2` Pydantic models in `trace_v2.py`
  - TraceEvent model (with all event types)
  - TaskContext model
  - EnvironmentInfo model
  - TraceStats model
  - Full Trace model
- [ ] Create validation utilities for schema
- [ ] Write unit tests for schema validation

### 1.3 Ingestion Layer (`src/ingestion/`)
- [ ] Create base parser interface in `parser.py`
- [ ] Implement LangGraph trace parser in `formats/langgraph.py`
  - Parse LangGraph JSON format
  - Extract events, nodes, edges
  - Handle nested structures
- [ ] Implement normalizer in `normalizer.py`
  - Convert parsed data to TraceSchemaV2
  - Calculate stats (tokens, latency, counts)
  - Handle missing/optional fields gracefully
- [ ] Create generic JSON fallback parser in `formats/generic.py`
- [ ] Write integration tests with sample traces

### 1.4 Basic Pre-analysis (`src/preanalysis/`)
- [ ] Implement basic pattern detection in `patterns.py`
  - Loop detection (identical tool calls repeated 3+)
  - Error finding (collect all error events)
  - Empty response detection
- [ ] Return structured pattern results with event IDs

### 1.5 Analysis Agent - Basic (`src/analysis/`)
- [ ] Create tool definitions in `tools.py`
  - `get_trace_summary` - returns stats overview
  - `get_event` - returns single event by ID
  - `find_errors` - returns all error events
  - `find_loops` - returns detected loop patterns
- [ ] Set up OpenRouter API client in `utils/config.py`
- [ ] Create analysis agent in `agent.py`
  - ReAct loop implementation using LangGraph
  - System prompt with citation requirements
  - Tool calling with guard rails
- [ ] Write prompts in `prompts.py`

### 1.6 Output Layer - Basic (`src/output/`)
- [ ] Create report generator in `report.py`
  - Markdown report template
  - Event ID citation formatting
  - Summary, timeline, root cause sections
- [ ] Create basic template in `templates/autopsy.md`

### 1.7 CLI (`src/cli.py`)
- [ ] Set up Typer CLI application
- [ ] Implement `analyze` command
  - Accept trace file path
  - Output report to stdout or file
  - Basic `--verbose` flag
- [ ] Add `--model` flag for model selection
- [ ] Create `main.py` entry point

### 1.8 Testing & Sample Data
- [ ] Create sample LangGraph traces in `tests/sample_traces/`
  - Successful trace
  - Loop failure trace
  - Error cascade trace
  - Timeout trace
- [ ] Write end-to-end tests

---

## Phase 2: Contracts & Enhanced Patterns

### 2.1 Contracts Module (`src/schema/contracts.py` & `src/preanalysis/contracts.py`)
- [ ] Define tool contract schemas
  - Tool name validation against allow-list
  - Input schema validation (JSON Schema/Pydantic)
  - Output schema validation
- [ ] Implement contract violation detector
  - Check tool existence
  - Validate input/output schemas
  - Flag missing metadata (latency, tokens)
- [ ] Return `contract_violations[]` with event IDs and fix suggestions

### 2.2 Enhanced Pattern Detection (`src/preanalysis/patterns.py`)
- [ ] Add additional patterns:
  - Retry storm detection
  - Context overflow detection
  - Hallucinated tool detection
  - Error cascade detection
  - Stale context detection
- [ ] Assign severity levels (Critical/High/Medium)
- [ ] Include evidence event IDs for each pattern

### 2.3 Root Cause Candidate Builder (`src/preanalysis/suspects.py`)
- [ ] Aggregate signals from patterns and contracts
- [ ] Generate hypotheses with confidence scores
- [ ] Link supporting events to each hypothesis
- [ ] Create pre-analysis bundle structure

### 2.4 Enhanced Analysis Tools
- [ ] Add new tools to `tools.py`:
  - `get_contract_violations`
  - `get_preanalysis_bundle`
  - `compare_events` (diff two events)
  - `get_context_at_event` (what model saw at that point)

### 2.5 LangChain Parser
- [ ] Implement LangChain callback log parser in `formats/langchain.py`
- [ ] Add to normalizer routing

---

## Phase 3: Smart Analysis & Artifacts

### 3.1 Semantic Search (`src/utils/embeddings.py`)
- [ ] Set up sentence-transformers for local embeddings
- [ ] Implement event embedding and indexing
- [ ] Create `search_events` tool for semantic search
- [ ] Add similarity threshold configuration

### 3.2 Advanced Analysis Agent
- [ ] Enhance system prompt for root cause chain generation
- [ ] Implement fix categorization logic:
  - Graph/Code fixes
  - Tool contract fixes
  - Prompt/policy fixes
  - Ops fixes
- [ ] Add confidence scoring to analysis

### 3.3 Artifact Generation (`src/output/artifacts.py`)
- [ ] Implement prompt patch generator
  - Extract problematic prompts
  - Generate patched versions
  - Write to `patched_system_prompt.txt`
- [ ] Implement code snippet generator
  - Retry policy snippets
  - Router logic patches
  - Tool validation snippets
- [ ] Add `--artifacts` CLI flag for output directory

### 3.4 Storage Layer
- [ ] Set up SQLite database for trace storage
- [ ] Create tables for traces, reports, artifacts
- [ ] Implement trace import/export
- [ ] Add `autopsy store` and `autopsy list` commands

### 3.5 Enhanced Reporting
- [ ] Add timeline visualization (ASCII/text)
- [ ] Add patch artifact references in report
- [ ] Add confidence indicators
- [ ] Add executive summary section

---

## Phase 4: Future Enhancements (Post-MVP)

### 4.1 Live Mode
- [ ] Create LangGraph callback hooks for real-time monitoring
- [ ] Implement loop detection interruption
- [ ] Add "intervention recommendation" mode
- [ ] WebSocket support for streaming analysis

### 4.2 Web UI (Streamlit)
- [ ] Create basic Streamlit dashboard
- [ ] Trace upload interface
- [ ] Interactive report viewer
- [ ] Event timeline visualization
- [ ] Fix recommendation cards

### 4.3 Additional Parsers
- [ ] AutoGen trace parser
- [ ] CrewAI trace parser
- [ ] OpenTelemetry trace parser

### 4.4 Advanced Features
- [ ] Comparative analysis (multiple traces)
- [ ] Regression detection
- [ ] Performance benchmarking
- [ ] Custom pattern definitions

---

## Technical Decisions

### Dependencies
```
# Core
python>=3.11
pydantic>=2.0
typer>=0.9
rich>=13.0  # for CLI formatting

# LLM & Agent
langgraph>=0.1
langchain-core>=0.1
openai>=1.0  # for OpenRouter compatibility

# Embeddings
sentence-transformers>=2.2

# Storage
sqlite3  # stdlib

# Testing
pytest>=7.0
pytest-asyncio>=0.21
```

### Configuration
- OpenRouter API key via `OPENROUTER_API_KEY` env var
- Default model configurable in `.env`
- Model override via `--model` CLI flag

### Error Handling
- Graceful degradation if LLM unavailable
- Pre-analysis always runs (deterministic)
- Clear error messages with suggestions

---

## Success Criteria

### Phase 1 Complete When:
1. Can parse a LangGraph trace JSON file
2. Can detect basic loops and errors
3. LLM agent produces a report with event ID citations
4. CLI `autopsy analyze trace.json` works end-to-end

### Phase 2 Complete When:
1. Contract validation catches tool misuse
2. Pre-analysis produces actionable hypotheses
3. All pattern types detected with severity levels

### Phase 3 Complete When:
1. Semantic search finds relevant events
2. Artifacts (patches) generated automatically
3. Reports include categorized fixes

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| LangGraph trace format changes | Abstract parser interface, version detection |
| LLM hallucinations | Strict tool allow-list, output validation |
| Large traces overflow context | Chunking, summarization, selective loading |
| OpenRouter rate limits | Caching, retry with backoff, local fallback |

---

## Getting Started

```bash
# Clone and setup
cd agent-autopsy
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your OPENROUTER_API_KEY

# Run
autopsy analyze ./tests/sample_traces/loop_failure.json
```
