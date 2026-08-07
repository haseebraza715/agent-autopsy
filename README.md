# Agent Autopsy

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](pyproject.toml)

**Local-first debugging for AI agent traces: deterministic failure detection with optional LLM root-cause analysis — no API keys, no network, no hosted dashboard.**

![Agent Autopsy demo](docs/demo.gif)

---

## Try it in 60 seconds

```bash
git clone https://github.com/haseebraza715/agent-autopsy.git
cd agent-autopsy
./scripts/demo.sh
```

One command, fully offline: no API keys, no network, and no setup beyond a
bootstrapped `.venv` on first run. The demo walks a real failing trace through
the whole pipeline — analyze, fix, diff.

**What you'll see:**

- A stuck agent run pinned to its root cause by the deterministic engine:

  ```
  CRITICAL infinite_loop: Same tool+input signature: web_search
  ```

- The findings turned into a ready-to-apply `LoopGuard` patch, and a failing-vs-fixed diff
  showing `empty_response, error_cascade, infinite_loop, timeout_pattern` only in the bad run.
- The fixed run flipping the verdict: `Health Score: 23/100 → 100/100` and CLI exit code `1 → 0` —
  the same exit-code gate your CI can key off.

---

## What it does

- **Ingests** LangGraph, LangChain, OpenTelemetry, and generic JSON traces, normalizing them into one schema.
- **Detects** failure patterns deterministically: infinite loops, retry storms, redundant tool calls, empty responses, error cascades, hallucinated tools, auth failures, timeouts, goal drift, stale context, token waste, context overflow, contract mismatches, inter-agent failures.
- **Reports** findings with evidence, event references, and a health score — as rich text or JSON.
- **Fixes** — detectors map to generated patch artifacts (loop guards, error boundaries) you can apply.
- **Compares** any two runs with `autopsy diff` to prove a fix changed behavior.
- **Surfaces** the same engine as a CLI, a Streamlit UI, an MCP server, and trace-capture helpers.

## How it works

Normalize any trace into a common event schema → run deterministic pattern detectors over the
event stream → emit a report with evidence and an exit code you can gate on → optionally hand the
normalized trace and findings to an LLM (OpenRouter, OpenAI, Anthropic, or Ollama) for a deeper
root-cause narrative. The default path is fully offline: the detectors alone already explain
*why* a run failed.

## Quick facts

| | |
|---|---|
| Language | Python 3.10+ |
| Dependencies | `pydantic`, `typer`, `rich`, `watchdog`, `pyyaml` |
| Offline | Yes — deterministic mode needs no network, no keys |
| Interfaces | CLI (`autopsy`), Streamlit UI, MCP server |
| License | MIT |

---

## Install options

| Install target | Command | Includes |
|---|---|---|
| Base CLI | `python -m pip install -e .` | CLI + deterministic analysis |
| LLM mode | `python -m pip install -e ".[llm]"` | Provider integrations for deeper synthesis |
| GUI | `python -m pip install -e ".[gui]"` | Streamlit app |
| MCP | `python -m pip install -e ".[mcp]"` | MCP server |
| Embeddings | `python -m pip install -e ".[embeddings]"` | Semantic drift detection |
| Full | `python -m pip install -e ".[full]"` | Everything above |

For contributors, `pip install -e ".[dev]"` installs everything needed to run the test suite.

## Core workflows

```bash
autopsy analyze trace.json --no-llm --no-embeddings   # deterministic analysis (offline)
autopsy analyze trace.json -o report.md --artifacts ./patches
autopsy diff baseline.json candidate.json             # before/after comparison
autopsy watch ./traces                                # analyze as traces are written
autopsy replay trace.json --step                      # step through the run event by event
autopsy benchmark --traces-dir ./traces               # batch trends over a trace set
```

## Optional LLM analysis

`autopsy analyze` uses the deterministic engine by default. Install `.[llm]`,
copy `.env.example` to `.env`, set one provider, and the same command adds a
root-cause narrative and richer fix suggestions. With no credentials configured,
it falls back to deterministic mode.

## Configuration

Common settings live in `.env`:

```env
PROVIDER=openrouter
OPENROUTER_API_KEY=
DEFAULT_MODEL=google/gemma-4-31b-it:free
TRACE_ENABLED=1
TRACE_DIR=./traces
```

Telemetry is opt-in and stays on your machine (`autopsy telemetry status | on | off`).

## Documentation

- [Quick start](docs/quickstart.md) · [Examples & traces](examples/README.md) · [Architecture](ARCHITECTURE.md)
- [Ingestion](docs/ingestion.md) · [Analysis pipeline](docs/analysis.md) · [Detector catalog](docs/patterns.md)
- [MCP server](docs/mcp.md) · [Plugins](docs/plugins.md) · [Demo playbook](docs/demo.md)

## Contributing

Contributions are welcome — new trace parsers, deterministic detectors, report
generation, UI polish, real-world fixtures. Start with [CONTRIBUTING.md](CONTRIBUTING.md)
and [good first issues](docs/good-first-issues.md).

Built by [Haseeb Raza](https://github.com/haseebraza715) · MIT licensed
