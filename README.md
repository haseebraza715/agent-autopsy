<div align="center">

# Agent Autopsy

**Intelligent trace analysis for AI agents**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/haseebraza715/agent-autopsy/blob/main/LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/haseebraza715/agent-autopsy?style=social)](https://github.com/haseebraza715/agent-autopsy)

*Automatically detect failures, loops, and issues in agent execution traces*

</div>

---

## Features

- **Multi-Format Support** — LangGraph + generic JSON (LangChain/OpenTelemetry detected but parsed generically)
- **Pattern Detection** — Loops, error cascades, hallucinated tools, and more
- **LLM Analysis** — AI-powered root cause analysis with event citations
- **Report Generation** — Structured markdown reports with fix recommendations
- **Artifact Generation** — Code patches for retry policies, loop guards
- **Trace Generation** — Generate test traces by running analysis agent
- **Lightweight** — Minimal dependencies, fast analysis

---

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Configure
cp .env.example .env  # Add your OPENROUTER_API_KEY

# Analyze a trace
python -m src.cli analyze trace.json
```

---

## Detected Patterns

| Pattern | Severity | Description |
|---------|----------|-------------|
| Infinite Loop | Critical | Same tool+input repeated 3+ times |
| Retry Storm | High | Same tool called repeatedly |
| Context Overflow | Critical | Token count exceeding limit |
| Hallucinated Tool | High | Unknown tool called |
| Empty Response | Medium | Empty LLM/tool output |
| Error Cascade | High | Sequential error propagation |

---

## CLI Usage

### Basic Commands

```bash
# Full analysis
python -m src.cli analyze trace.json -o report.md

# Generate patches
python -m src.cli analyze trace.json --artifacts ./patches/

# Without LLM (deterministic only)
python -m src.cli analyze trace.json --no-llm

# Quick summary
python -m src.cli summary trace.json

# Validate format
python -m src.cli validate trace.json
```

### Trace Generation & Analysis Scripts

```bash
# Generate traces by running analysis agent
python scripts/generate_traces.py --min-runs 20

# Verify all traces
python scripts/verify_traces.py

# Analyze all traces and generate reports
python scripts/analyze_traces.py
```

**Script Options:**
| Flag | Description |
|------|-------------|
| `--min-runs` | Minimum number of runs (default: 20) |
| `--stop-on-failure` | Stop after finding a failure |
| `--traces-dir` | Directory for trace files |
| `--reports-dir` | Directory for report files |
| `--quiet` | Suppress progress output |

**CLI Options:**
| Flag | Description |
|------|-------------|
| `-o, --output` | Output file path |
| `--artifacts` | Patch output directory |
| `--model` | Model override |
| `-v, --verbose` | Detailed output |
| `--no-llm` | Skip LLM analysis |

---

## Configuration

```env
OPENROUTER_API_KEY=your_key_here
DEFAULT_MODEL=meta-llama/llama-3.1-8b-instruct
LOG_LEVEL=INFO

# Tracing Configuration
TRACE_ENABLED=1          # Enable/disable trace capture (1/0)
TRACE_DIR=./traces       # Directory for trace files
TRACE_MAX_CHARS=5000     # Max chars per field (truncation)
```

---

## Trace Capture

Agent Autopsy can automatically capture execution traces from your LangChain/LangGraph agents.

### Enabling Trace Capture

Tracing is enabled by default. Set `TRACE_ENABLED=0` to disable.

```python
from src.tracing import TraceSaver, start_trace, end_trace

# Start trace capture
trace_handler, run_id = start_trace()

# Attach to your agent/graph
result = graph.invoke(
    input_state,
    config={"callbacks": [trace_handler]}
)

# Save trace (always in finally block)
end_trace(trace_handler)
# Output: Trace saved: traces/20241231_123456_abc123.json
```

### Trace Schema

Each trace event includes:
- `event_id` - Incrementing event ID
- `ts` - ISO timestamp
- `type` - Event type (llm_start, llm_end, tool_start, tool_end, error, etc.)
- `name` - Component name (model, tool, chain)
- `input` - Input data (redacted for secrets)
- `output` - Output data (truncated if long)
- `latency_ms` - Execution time
- `metadata` - Additional context (tokens, run_id, etc.)

### Analyzing Captured Traces

```bash
# Run autopsy on a captured trace
python -m src.cli autopsy-run traces/20241231_123456_abc123.json

# Specify output location
python -m src.cli autopsy-run traces/my_trace.json -o report.md
```

---

## Project Structure

```
agent-autopsy/
├── src/
│   ├── ingestion/      # Trace parsing
│   ├── preanalysis/    # Pattern detection
│   ├── analysis/       # LLM analysis
│   ├── output/         # Report generation
│   ├── tracing/        # Trace capture for agents
│   ├── utils/          # Configuration
│   └── cli.py          # CLI interface
├── scripts/            # Trace generation & analysis scripts
│   ├── modules/        # Reusable modules
│   ├── generate_traces.py
│   ├── analyze_traces.py
│   └── verify_traces.py
├── tests/
├── traces/             # Captured trace files
├── reports/            # Generated reports
└── docs/               # Documentation
```

---

## Architecture

![Architecture](diagrams/architecture.png)

For detailed diagrams:
- [System Flow](diagrams/system_flow.mmd) - Complete analysis pipeline
- [Trace Generation](diagrams/trace_generation.mmd) - Trace generation workflow
- [Pattern Detection](diagrams/pattern_detection.mmd) - Pattern detection flow

---

## Documentation

- [Architecture](docs/architecture.md) — System overview
- [Quick Start](docs/quickstart.md) — Installation guide
- [Ingestion](docs/ingestion.md) — Trace format support
- [Analysis](docs/analysis.md) — Pattern detection & LLM analysis
- [Patterns](docs/patterns.md) — Detected failure patterns
- [Output](docs/output.md) — Report generation
- [Scripts](scripts/README.md) — Trace generation and analysis scripts

---

## Contributing

PRs welcome! Feel free to submit issues or spread the word.

---

<div align="center">

MIT © [Haseeb Raza](https://github.com/haseebraza715)

</div>
