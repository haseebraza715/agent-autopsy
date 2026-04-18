<div align="center">

# Agent Autopsy

### Forensic debugging for AI agent traces — in your terminal, in under a second.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](pyproject.toml)
[![GitHub stars](https://img.shields.io/github/stars/haseebraza715/agent-autopsy?style=social)](https://github.com/haseebraza715/agent-autopsy)

![Agent Autopsy — deterministic + LLM analysis of a failing trace](docs/images/autopsy-demo.gif)

**[Try it live →](https://autopsyagent.streamlit.app/)**

</div>

---

## The problem

Your agent failed. You have a 5 MB JSON trace. Now what?

`grep`ing won't surface the loop. The LangGraph Studio upload is slow and public-cloud. Your homegrown Python script catches the one bug you wrote it for and misses the next three.

## The fix

```bash
autopsy analyze trace.json
```

One second later, a terminal report shows you the infinite loop at event 42, the hallucinated tool call at event 58, and three retry storms between them — with citation event IDs you can jump to.

Want deeper analysis? Add `--stream` and an LLM synthesises root cause with cited evidence. Works with Ollama, OpenAI, Anthropic, OpenRouter.

---

## Quickstart

```bash
pip install -e ".[cli]"
autopsy analyze examples/traces/loop_failure.json --no-llm
```

No API key. No account. No network call. Works on your laptop, in CI, on air-gapped boxes.

---

## Feature tour

<details open>
<summary><b>Thirteen deterministic pattern detectors</b></summary>

Built-in detectors for infinite loops, retry storms, context overflow, hallucinated tools, empty responses, error cascades, stale context, semantic drift, token waste, auth failures, and more. All run sub-second, no LLM required. See [docs/patterns.md](docs/patterns.md).

</details>

<details>
<summary><b>Optional LLM root-cause synthesis</b></summary>

```bash
autopsy analyze trace.json --stream                    # tokens stream live
autopsy analyze trace.json --provider ollama --model llama3.1:8b   # local
```

Structured Pydantic output, citations validated against the trace (no hallucinated event IDs), disk-cached so re-runs are instant.

</details>

<details>
<summary><b><code>autopsy watch</code> — auto-analyse new traces</b></summary>

```bash
autopsy watch ./traces
```

Point it at your trace output directory. Every new `.json` gets analysed on write. Perfect for the agent-dev inner loop.

</details>

<details>
<summary><b><code>autopsy diff</code> — compare two runs</b></summary>

```bash
autopsy diff baseline.json candidate.json -f json
```

Which events appeared or disappeared, which patterns fired in one run but not the other, which tool calls have different arguments. Unique — hosted tools don't do this well.

</details>

<details>
<summary><b><code>autopsy replay</code> — step through a trace</b></summary>

```bash
autopsy replay trace.json --from 42 --speed 2
```

Interactive, debugger-style playback. Understand what the agent was *thinking* event by event.

</details>

<details>
<summary><b>Plugins and MCP</b></summary>

Drop-in parser, detector, report, and fix-generator plugins — see [docs/plugins.md](docs/plugins.md). MCP server exposes analysis tools to any MCP-compatible client with optional bearer-token auth for SSE — see [docs/mcp.md](docs/mcp.md).

</details>

<details>
<summary><b>Streamlit web UI</b></summary>

```bash
pip install -e ".[gui]"
streamlit run app.py
```

Custom dark theme, batch analysis, trace viewer, live LLM streaming. Prefer the terminal? Ignore this.

</details>

---

## How it compares

| | Agent Autopsy | LangSmith | `grep` + scripts |
|---|:-:|:-:|:-:|
| Works offline | yes | no | yes |
| No account required | yes | no | yes |
| Sub-second analysis | yes | no | yes |
| Pattern library | 13+ | yes | none |
| LLM root cause | yes | yes | no |
| Streaming output | yes | yes | no |
| Trace diffing | yes | partial | no |
| Local LLM (Ollama) | yes | no | n/a |
| Data stays on your box | yes | no | yes |

Agent Autopsy is not a LangSmith replacement — it's for the 90% of debugging that happens on your laptop, in CI, or where you can't ship traces off-box.

---

## Install

Pick the smallest group you need:

| Group | Command | Use for |
|-------|---------|---------|
| `cli` | `pip install -e ".[cli]"` | Terminal only |
| `gui` | `pip install -e ".[gui]"` | Web UI |
| `mcp` | `pip install -e ".[mcp]"` | MCP server |
| `embeddings` | `pip install -e ".[embeddings]"` | Semantic drift (1.5 GB model) |
| `full` | `pip install -e ".[full]"` | Everything |

---

## Command reference

```bash
# Analysis
autopsy analyze trace.json                     # deterministic + LLM (if key set)
autopsy analyze trace.json --no-llm            # fast, offline
autopsy analyze trace.json --stream            # stream LLM tokens live
autopsy analyze trace.json -f json | jq .      # machine-readable

# Daily drivers
autopsy watch ./traces                         # auto-analyse new files
autopsy diff baseline.json candidate.json      # compare two runs
autopsy replay trace.json --from 42 --speed 2  # step-by-step

# Utilities
autopsy summary trace.json                     # one-screen overview
autopsy fixes trace.json                       # remediation suggestions
autopsy benchmark --traces-dir ./traces        # batch metrics
autopsy telemetry on                           # opt in to anonymous local logs

# Shell completion
autopsy --install-completion
```

**Exit codes:** `0` clean · `1` findings · `2` tool / parse error. `NO_COLOR=1` disables colors.

---

## Configuration

A single `.env` covers all providers:

```env
OPENROUTER_API_KEY=...          # or OPENAI_API_KEY / ANTHROPIC_API_KEY
DEFAULT_MODEL=google/gemma-4-31b-it:free
TRACE_ENABLED=1
TRACE_DIR=./traces
MCP_SSE_TOKEN=...               # only if exposing MCP over SSE
```

Telemetry is off by default. Opt-in is local-only: anonymous JSON appended to `~/.cache/agent-autopsy/telemetry-events.jsonl`. Nothing leaves your machine.

---

## Capturing traces from your agent

```python
from src.tracing import start_trace, end_trace

trace_handler, run_id = start_trace()
result = graph.invoke(state, config={"callbacks": [trace_handler]})
end_trace(trace_handler)
```

Outputs land in `TRACE_DIR`. Feed them straight into `autopsy analyze`.

---

## Documentation

| | |
|---|---|
| **Get started** | [Quick Start](docs/quickstart.md) · [Demo Playbook](docs/demo.md) · [Examples](examples/README.md) |
| **Deep dives** | [Architecture](ARCHITECTURE.md) · [Patterns](docs/patterns.md) · [Analysis pipeline](docs/analysis.md) |
| **Extend it** | [Plugins](docs/plugins.md) · [Extensions](docs/extensions.md) · [MCP server](docs/mcp.md) |
| **Roadmap** | [Launch post draft](docs/launch-post.md) · [Roadmap](ROADMAP.md) · [Good first issues](docs/good-first-issues.md) |
| **Planning** | [Improvement plan v1](docs/unified-improvement-plan.md) · [v2 best-in-class](docs/v2-best-in-class-plan.md) · [Implementation audit](docs/implementation-audit.md) |

---

## Contributing

Good first issues are labelled in the tracker and listed in [docs/good-first-issues.md](docs/good-first-issues.md). Adding a new pattern detector takes about 15 minutes — see [CONTRIBUTING.md](CONTRIBUTING.md). Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before filing issues.

---

<div align="center">

Built by [Haseeb Raza](https://github.com/haseebraza715) · MIT licensed

</div>
