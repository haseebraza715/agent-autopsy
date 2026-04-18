<div align="center">

# 🔍 Agent Autopsy

**Intelligent trace analysis for AI agents**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/haseebraza715/agent-autopsy/blob/main/LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/haseebraza715/agent-autopsy?style=social)](https://github.com/haseebraza715/agent-autopsy)

*Automatically detect failures, loops, and issues in agent execution traces*

![HD demo: deterministic pre-analysis + LLM synthesis on loop_failure.json](docs/images/autopsy-demo.gif)

**[Try it live](https://autopsyagent.streamlit.app/)** | [Documentation](docs/) | [Report Issue](https://github.com/haseebraza715/agent-autopsy/issues)

</div>

---

## Overview

Agent Autopsy helps debug AI agent runs by turning raw traces into actionable failure analysis.

Core capabilities:

- Deterministic pattern detection (loops, retries, context/auth/timeout issues, drift)
- Optional LLM-assisted root cause analysis with cited evidence
- CLI + Streamlit UI + MCP server workflows
- Multi-agent trace support, comparison, benchmark mode, and live monitoring
- Extensible plugin interfaces for custom parsers/detectors/reports/fixes

## Setup

Install the smallest set you need (see `pyproject.toml` optional groups):

```bash
pip install -e ".[cli]"            # CLI only (Typer/Rich + core)
pip install -e ".[llm]"            # + LangGraph / LangChain / OpenAI client
pip install -e ".[gui]"            # + Streamlit
pip install -e ".[mcp]"            # + MCP SDK
pip install -e ".[embeddings]"     # + sentence-transformers (semantic drift)
pip install -e ".[dev]"            # + pytest
pip install -e ".[full]"          # everything (largest install)
```

Quick try without any LLM API key:

```bash
pip install -e ".[cli]"
autopsy analyze examples/traces/loop_failure.json --no-llm --no-embeddings
```

### CLI exit codes

| Code | Meaning |
|------|---------|
| 0 | No errors in trace stats and no deterministic signals |
| 1 | Findings (signals or trace errors) |
| 2 | Parse / validation / usage error |

### Daily-driver commands (local-first)

```bash
autopsy analyze trace.json --no-llm -q -f text          # fast deterministic report, plain text
autopsy analyze trace.json -f json | jq .             # machine-readable
autopsy diff baseline.json candidate.json -f json     # rich diff (also: compare)
autopsy watch ./traces --pattern '*.json'             # analyze new traces on write
autopsy replay trace.json --from 42 --speed 2 --delay 0.2
```

LLM options: `--provider ollama --model llama3.1:8b`, `--stream`, `--no-cache` (bypass `~/.cache/agent-autopsy/`). Shell completion: `autopsy --install-completion`.

**Telemetry (optional):** off by default. `autopsy telemetry on` appends anonymous JSON lines (command, exit code, signal count, hashed run id) to `~/.cache/agent-autopsy/telemetry-events.jsonl`, or set `AUTOPSY_TELEMETRY=1`.

**Docs:** [Launch post draft](docs/launch-post.md) · [Demo GIF how-to](docs/demo-gif.md) · [Roadmap](ROADMAP.md) · [Good first issues](docs/good-first-issues.md)

## Usage

### Web App

```bash
pip install -e ".[gui]"
streamlit run app.py
```

### CLI

```bash
autopsy analyze examples/traces/loop_failure.json --no-llm
# or: python -m src.cli analyze trace.json --no-llm
```

### MCP Server

```bash
python -m src.mcp --transport stdio
```

### Common Commands

```bash
python -m src.cli summary trace.json
python -m src.cli compare baseline.json candidate.json   # alias: diff
python -m src.cli benchmark --traces-dir ./traces
python -m src.cli fixes trace.json
python scripts/eval_detectors.py                         # detector corpus metrics (CI)
```

---

## Features

- **Web GUI** — Interactive Streamlit interface for trace analysis (optional live LLM stream via LangGraph `stream_mode`)
- **Pattern Detection** — Loops, retries, auth/timeouts, drift, stale context, token waste, and more
- **LLM Analysis** — AI-powered root cause analysis with event citations
- **Multi-Format** — LangGraph and generic JSON, plus experimental LangChain/OpenTelemetry parsing with graceful fallback
- **Reports** — Structured markdown reports with fix recommendations
- **Trace Capture** — Automatic trace collection from LangChain/LangGraph agents
- **MCP Integration** — Exposes analysis tools/resources/prompts for MCP-compatible clients
- **Advanced Ops** — Trace comparison, benchmark mode, live monitoring alerts, and generated fix suggestions
- **Extensible Plugins** — Custom parsers, detectors, report templates, fix generators, and visualizations

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

## Web GUI Features

- **Home Dashboard** — Quick access to recent traces and reports
- **Analyze Trace** — Upload and analyze with interactive results
- **Trace Viewer** — Browse events with filtering and detailed views
- **Batch Analysis** — Process multiple traces at once
- **Reports** — View and download generated reports

---

## Configuration

```env
OPENROUTER_API_KEY=your_key_here
DEFAULT_MODEL=xiaomi/mimo-v2-flash:free
TRACE_ENABLED=1
TRACE_DIR=./traces
```

---

## Trace Capture

```python
from src.tracing import start_trace, end_trace

trace_handler, run_id = start_trace()
result = graph.invoke(input_state, config={"callbacks": [trace_handler]})
end_trace(trace_handler)
```

---

## Documentation

- [Architecture](ARCHITECTURE.md) — System overview with Mermaid diagram
- [Architecture (Detailed)](docs/architecture.md) — Extended component details
- [Quick Start](docs/quickstart.md) — Installation guide
- [Patterns](docs/patterns.md) — Detected failure patterns
- [MCP Server](docs/mcp.md) — MCP tools, resources, prompts, and transports
- [Extension Guide](docs/extensions.md) — Add parsers, detectors, reports, and MCP capabilities
- [Plugin System](docs/plugins.md) — Build and register custom extensions
- [Demo Playbook](docs/demo.md) — 5-minute project walkthrough
- [Examples](examples/README.md) — Curated sample traces and expected outcomes

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), and [CHANGELOG.md](CHANGELOG.md).

---

<div align="center">

MIT © [Haseeb Raza](https://github.com/haseebraza715)

</div>
