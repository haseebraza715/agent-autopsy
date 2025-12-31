# Agent Autopsy - Development TODO

## Phase 1 MVP - COMPLETED

### Project Setup
- [x] Create `requirements.txt` with dependencies
- [x] Create `.env.example` file
- [x] Create directory structure
- [x] Set up basic logging

### Schema Layer
- [x] Create `src/schema/trace_v2.py` - Pydantic models for TraceSchemaV2
- [x] Create `src/schema/contracts.py` - Tool schema definitions

### Ingestion Layer
- [x] Create `src/ingestion/parser.py` - Base parser interface
- [x] Create `src/ingestion/normalizer.py` - Normalize to TraceSchemaV2
- [x] Create `src/ingestion/formats/langgraph.py` - LangGraph trace parser
- [x] Create `src/ingestion/formats/generic.py` - Generic JSON fallback

### Pre-analysis Layer
- [x] Create `src/preanalysis/patterns.py` - Loop & error detection
- [x] Create `src/preanalysis/contracts.py` - Contract validation
- [x] Create `src/preanalysis/suspects.py` - Root cause builder

### Analysis Agent
- [x] Create `src/utils/config.py` - OpenRouter client setup
- [x] Create `src/analysis/tools.py` - Agent tools (get_event, find_errors, etc.)
- [x] Create `src/analysis/prompts.py` - System prompts
- [x] Create `src/analysis/agent.py` - ReAct agent with LangGraph

### Output Layer
- [x] Create `src/output/report.py` - Markdown report generator
- [x] Create `src/output/templates/autopsy.md` - Report template
- [x] Create `src/output/artifacts.py` - Artifact generator

### CLI
- [x] Create `src/cli.py` - Typer CLI with analyze command
- [x] Create `src/main.py` - Entry point

### Testing
- [x] Create `tests/sample_traces/` directory
- [x] Create sample loop failure trace
- [x] Create sample successful trace
- [x] Create sample hallucinated tool trace
- [x] Write basic tests

---

## Phase 2 - Next Steps

- [ ] Add LangChain callback log parser
- [ ] Enhanced pattern detection with severity tuning
- [ ] Add semantic search with embeddings (`src/utils/embeddings.py`)
- [ ] Add SQLite storage for traces and reports
- [ ] Improve artifact generation quality
- [ ] Add `autopsy store` and `autopsy list` commands

## Phase 3 - Advanced Features

- [ ] Semantic search over events
- [ ] Better LLM analysis with multi-turn reasoning
- [ ] Comparative analysis (diff two traces)
- [ ] Performance benchmarking

## Phase 4 - Future

- [ ] Live mode with LangGraph callback hooks
- [ ] Streamlit UI for interactive analysis
- [ ] AutoGen trace parser
- [ ] CrewAI trace parser
- [ ] OpenTelemetry trace parser

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Edit .env with your OPENROUTER_API_KEY

# Run analysis
python -m src.cli analyze ./tests/sample_traces/loop_failure.json

# Run without LLM
python -m src.cli analyze ./tests/sample_traces/loop_failure.json --no-llm

# Run tests
pytest tests/ -v
```

---

## Notes

- LangGraph parser handles most common trace formats
- Generic parser serves as fallback for unknown formats
- Pre-analysis always runs first (deterministic)
- LLM analysis is optional (use --no-llm flag)
- All claims in reports should cite event IDs
