# Agent Autopsy

### Local-first debugging for AI agent traces

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](pyproject.toml)
[![GitHub stars](https://img.shields.io/github/stars/haseebraza715/agent-autopsy?style=social)](https://github.com/haseebraza715/agent-autopsy)

Find failure patterns, inspect evidence, and generate fix guidance from LangGraph, LangChain, OpenTelemetry, or generic JSON traces without shipping them to a hosted dashboard first.

![Agent Autopsy demo](docs/images/autopsy-demo.gif)

**[Live demo](https://autopsyagent.streamlit.app/)** ·
**[Quick start](docs/quickstart.md)** ·
**[Examples](examples/README.md)** ·
**[Architecture](ARCHITECTURE.md)**

---

## Why this exists

When an agent run fails, the painful part usually is not collecting the trace. It is figuring out what actually went wrong quickly enough to fix it.

Agent Autopsy is built for that moment:

- You have a large trace file and need a fast local read on what happened.
- You want deterministic signal detection before paying for LLM reasoning.
- You need something that works in the terminal, in CI, or in environments where traces should stay on your machine.

In deterministic mode, Agent Autopsy runs fully offline. If you enable LLM analysis, it can synthesize a deeper root-cause report using OpenRouter, OpenAI, Anthropic, or Ollama.

---

## What Agent Autopsy does

Agent Autopsy runs a deterministic-first pipeline:

1. Ingest a trace from LangGraph, LangChain, OpenTelemetry, or a generic JSON shape.
2. Normalize it into a common trace schema.
3. Detect failure patterns such as loops, retry storms, hallucinated tools, auth failures, timeouts, context overflow, token waste, stale context, and contract mismatches.
4. Build a report with evidence and event references.
5. Optionally hand the normalized trace and deterministic findings to an LLM for a stronger root-cause narrative and fix recommendations.

You can use it through:

- A CLI for local debugging and CI workflows
- A Streamlit UI for browsing traces interactively
- An MCP server so other tools can analyze traces programmatically
- Trace-capture helpers for LangChain and LangGraph style runs

---

## Quickstart

### Requirements

- Python 3.10 or newer
- `pip`

If `python3 --version` reports 3.9 or lower, install Python 3.10+ first. The project uses modern type syntax and will not run on Python 3.9.

### Fastest path

```bash
git clone https://github.com/haseebraza715/agent-autopsy.git
cd agent-autopsy

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .

autopsy analyze examples/traces/loop_failure.json --no-llm --no-embeddings
```

That gives you the core CLI with deterministic analysis only:

- No API key
- No account
- No hosted upload
- No network call

### Useful next commands

```bash
autopsy summary examples/traces/hallucinated_tool.json
autopsy validate examples/traces/loop_failure.json
autopsy fixes examples/traces/loop_failure.json
autopsy diff examples/traces/loop_failure.json examples/traces/hallucinated_tool.json
```

---

## Install options

The base install is enough for the CLI and deterministic analysis.

| Install target | Command | Includes |
|---|---|---|
| Base CLI | `python -m pip install -e .` | CLI + deterministic analysis |
| LLM mode | `python -m pip install -e ".[llm]"` | Provider integrations for deeper synthesis |
| GUI | `python -m pip install -e ".[gui]"` | Streamlit app |
| MCP | `python -m pip install -e ".[mcp]"` | MCP server |
| Embeddings | `python -m pip install -e ".[embeddings]"` | Sentence-transformers for semantic drift |
| Full | `python -m pip install -e ".[full]"` | Everything above |

If you want the shortest reliable first-run path, start with the base install and add extras only when you need them.

---

## Core workflows

### 1. Analyze one trace

```bash
autopsy analyze trace.json
autopsy analyze trace.json --no-llm
autopsy analyze trace.json --no-llm --no-embeddings
autopsy analyze trace.json -f json
autopsy analyze trace.json -o report.md --artifacts ./patches
```

What you get:

- Trace summary
- Deterministic findings and hypotheses
- Report text or JSON
- Optional fix artifacts

### 2. Compare two runs

```bash
autopsy diff baseline.json candidate.json
autopsy diff baseline.json candidate.json -f json
```

Useful for:

- Regression checks
- Prompt or toolchain changes
- Evaluating whether a “fix” really changed agent behavior

### 3. Watch a trace directory

```bash
autopsy watch ./traces
```

This is a nice inner-loop workflow when your agent writes JSON traces continuously during development.

### 4. Replay the run event by event

```bash
autopsy replay trace.json --from 42 --speed 2
autopsy replay trace.json --step
```

Use this when you want a debugger-style walkthrough of the trace rather than a summary.

### 5. Batch benchmark a trace set

```bash
autopsy benchmark --traces-dir ./traces
```

This helps answer questions like:

- Are failures getting better or worse?
- Which patterns are most common?
- Did a recent change degrade success rate or latency?

---

## Optional LLM analysis

If you install `.[llm]`, Agent Autopsy can synthesize a stronger root-cause explanation on top of deterministic findings.

Copy the example environment file:

```bash
cp .env.example .env
```

Then configure one provider:

```env
# Pick one provider: openrouter | openai | anthropic | ollama
PROVIDER=openrouter
OPENROUTER_API_KEY=your_key_here
DEFAULT_MODEL=google/gemma-4-31b-it:free
```

Example commands:

```bash
autopsy analyze trace.json
autopsy analyze trace.json --stream
autopsy analyze trace.json --provider ollama --model llama3.1:8b
autopsy analyze trace.json --no-cache
```

Notes:

- If no valid provider credentials are configured, `analyze` falls back to deterministic mode.
- `--stream` streams LLM output live in the terminal.
- `--no-cache` bypasses the disk cache for LLM responses.

---

## Supported inputs

Agent Autopsy automatically detects and normalizes these trace shapes:

- LangGraph
- LangChain
- OpenTelemetry
- Generic JSON traces
- Plugin-defined trace parsers

Normalization gives the rest of the pipeline a consistent schema for:

- Event IDs
- Event types
- Timing
- Token usage
- Errors
- Tool calls
- Agent handoffs

See [docs/ingestion.md](docs/ingestion.md) for details.

---

## Built-in detectors

The deterministic layer includes detectors for:

- Infinite loops
- Retry storms
- Redundant tool calls
- Empty responses
- Error cascades
- Hallucinated tools
- Auth and permission failures
- Timeout patterns
- Goal drift
- Stale context
- Token waste
- Inter-agent failures
- Context overflow
- Tool contract mismatches

See [docs/patterns.md](docs/patterns.md) for the detector catalog and tuning notes.

---

## Streamlit UI

If you want a browser UI instead of terminal output:

```bash
python -m pip install -e ".[gui]"
streamlit run app.py
```

The Streamlit app includes:

- Single-trace analysis
- Batch analysis
- Trace viewer
- Reports
- Settings and provider configuration

You can also try the hosted demo at [autopsyagent.streamlit.app](https://autopsyagent.streamlit.app/).

---

## MCP server

If you want to expose Agent Autopsy to an MCP-compatible client:

```bash
python -m pip install -e ".[mcp]"

autopsy-mcp --transport stdio
autopsy-mcp --transport streamable-http --mount-path /mcp
```

The MCP layer exposes tools for:

- Analyzing traces
- Detecting patterns
- Validating trace structure
- Comparing runs
- Listing traces
- Looking up event details
- Suggesting fixes
- Monitoring trace directories

For HTTP transports, bearer-token auth can be enabled with `MCP_SSE_TOKEN`.

See [docs/mcp.md](docs/mcp.md) for setup and transport details.

---

## Capturing traces from your own agent

Agent Autopsy includes trace-capture helpers for LangChain and LangGraph style workflows.

```python
from src.tracing import start_trace, end_trace

trace_handler, run_id = start_trace()
result = graph.invoke(state, config={"callbacks": [trace_handler]})
end_trace(trace_handler)
```

By default, traces are written to `./traces` unless you override `TRACE_DIR`.

Relevant settings:

```env
TRACE_ENABLED=1
TRACE_DIR=./traces
TRACE_MAX_CHARS=5000
```

See [src/tracing/trace_saver.py](src/tracing/trace_saver.py) and [docs/quickstart.md](docs/quickstart.md) for more.

---

## Configuration

Common settings live in `.env`:

```env
PROVIDER=openrouter
OPENROUTER_API_KEY=
OPENAI_API_KEY=
OPENAI_API_BASE=
OLLAMA_BASE_URL=http://127.0.0.1:11434
DEFAULT_MODEL=google/gemma-4-31b-it:free
FALLBACK_MODEL=google/gemma-4-26b-a4b-it:free
TRACE_ENABLED=1
TRACE_DIR=./traces
```

Telemetry is opt-in and local-only:

```bash
autopsy telemetry status
autopsy telemetry on
autopsy telemetry off
```

When enabled, telemetry is appended to a local JSONL file under the cache directory. Nothing is sent by default.

---

## Documentation map

| Topic | Link |
|---|---|
| Fast onboarding | [docs/quickstart.md](docs/quickstart.md) |
| Example traces and walkthroughs | [examples/README.md](examples/README.md) |
| Architecture overview | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Ingestion and format detection | [docs/ingestion.md](docs/ingestion.md) |
| Analysis pipeline | [docs/analysis.md](docs/analysis.md) |
| Detector catalog | [docs/patterns.md](docs/patterns.md) |
| MCP setup | [docs/mcp.md](docs/mcp.md) |
| Plugins and extension points | [docs/plugins.md](docs/plugins.md) and [docs/extensions.md](docs/extensions.md) |
| Demo playbook | [docs/demo.md](docs/demo.md) |
| Roadmap and plans | [ROADMAP.md](ROADMAP.md) and [docs/unified-improvement-plan.md](docs/unified-improvement-plan.md) |

---

## Contributing

Contributions are welcome, especially in these areas:

- New trace parsers
- New deterministic detectors
- Better report generation
- UI polish
- Real-world fixtures and evaluation traces
- Documentation and onboarding

Start with:

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [docs/good-first-issues.md](docs/good-first-issues.md)
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

Built by [Haseeb Raza](https://github.com/haseebraza715) · MIT licensed
