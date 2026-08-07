# Agent Autopsy

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](pyproject.toml)

**Debug AI agent traces locally: deterministic failure detection, fully offline, no API keys. Optional LLM root-cause analysis.**

<video controls autoplay muted loop playsinline width="100%" src="https://github.com/haseebraza715/agent-autopsy/raw/main/docs/demo.mp4"></video>

Prefer a GIF? [docs/demo.gif](docs/demo.gif)

---

## Try it in 60 seconds

```bash
git clone https://github.com/haseebraza715/agent-autopsy.git
cd agent-autopsy
./scripts/demo.sh
```

One command, fully offline: no API keys, no network, no setup beyond a bootstrapped `.venv` on first run. The demo walks a real failing trace through the whole pipeline: analyze, fix, diff.

**What you'll see:**

- Root cause pinned deterministically: `CRITICAL infinite_loop: Same tool+input signature: web_search`
- A ready-to-apply `LoopGuard` patch, plus a failing-vs-fixed diff isolating every failure pattern to the bad run
- The verdict flips: health `23/100 → 100/100`, CLI exit `1 → 0`. A gate your CI can enforce

---

## What it does

- **Ingests** LangGraph, LangChain, OpenTelemetry, and generic JSON traces into one schema
- **Detects** failure patterns deterministically: infinite loops, retry storms, empty responses, error cascades, hallucinated tools, timeouts, and more
- **Reports** findings with evidence and a health score, as rich text or JSON
- **Fixes**: generates patch artifacts (loop guards, error boundaries) from findings
- **Compares** any two runs with `autopsy diff` to prove a fix changed behavior
- **Surfaces** the same engine as a CLI, Streamlit UI, MCP server, and trace-capture helpers

## How it works

Normalize any trace into a common event schema → run deterministic pattern detectors over the event stream → emit a report with evidence and a gatable exit code. Point an LLM at the normalized trace for a deeper root-cause narrative, but the default path is fully offline.

## Quick facts

| | |
|---|---|
| Language | Python 3.10+ |
| Dependencies | `pydantic`, `typer`, `rich`, `watchdog`, `pyyaml` |
| Offline | Yes: deterministic mode needs no network, no keys |
| Interfaces | CLI (`autopsy`), Streamlit UI, MCP server |
| License | MIT |

---

## Links

[Quick start](docs/quickstart.md) · [Architecture](ARCHITECTURE.md) · [Contributing](CONTRIBUTING.md) · [Good first issues](docs/good-first-issues.md)

Contributions are welcome: new trace parsers, deterministic detectors, UI polish, real-world fixtures.

Built by [Haseeb Raza](https://github.com/haseebraza715) · MIT licensed
