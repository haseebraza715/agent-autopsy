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
