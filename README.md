<div align="center">

# 🔍 Agent Autopsy

**Intelligent trace analysis for AI agents**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/haseebraza715/agent-autopsy/blob/main/LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/haseebraza715/agent-autopsy?style=social)](https://github.com/haseebraza715/agent-autopsy)

*Automatically detect failures, loops, and issues in agent execution traces*

**[Try it live](https://autopsyagent.streamlit.app/)** | [Documentation](docs/) | [Report Issue](https://github.com/haseebraza715/agent-autopsy/issues)

</div>

---

## Quick Start

### Web App (Recommended)

**[Use the live app](https://autopsyagent.streamlit.app/)**

Or run locally:
```bash
pip install -r requirements.txt
streamlit run app.py
```

### CLI
```bash
python -m src.cli analyze trace.json
```

### MCP Server
```bash
python -m src.mcp --transport stdio
```

---

## Features

- **Web GUI** — Interactive Streamlit interface for trace analysis
- **Pattern Detection** — Loops, retries, auth/timeouts, drift, stale context, token waste, and more
- **LLM Analysis** — AI-powered root cause analysis with event citations
- **Multi-Format** — LangGraph and generic JSON, plus experimental LangChain/OpenTelemetry parsing with graceful fallback
- **Reports** — Structured markdown reports with fix recommendations
- **Trace Capture** — Automatic trace collection from LangChain/LangGraph agents
- **MCP Integration** — Exposes analysis tools/resources/prompts for MCP-compatible clients

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

- [Architecture](docs/architecture.md) — System overview
- [Quick Start](docs/quickstart.md) — Installation guide
- [Patterns](docs/patterns.md) — Detected failure patterns
- [MCP Server](docs/mcp.md) — MCP tools, resources, prompts, and transports
- [Extension Guide](docs/extensions.md) — Add parsers, detectors, reports, and MCP capabilities
- [Demo Playbook](docs/demo.md) — 5-minute project walkthrough
- [Examples](examples/README.md) — Curated sample traces and expected outcomes

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), and [CHANGELOG.md](CHANGELOG.md).

---

<div align="center">

MIT © [Haseeb Raza](https://github.com/haseebraza715)

</div>
