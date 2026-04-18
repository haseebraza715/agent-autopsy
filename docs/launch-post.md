# Launch post draft: Agent Autopsy

**Title:** Agent Autopsy: a local-first CLI for debugging LangGraph and LangChain traces

**Audience:** Engineers shipping agents who hit weird failures at night and do not want another hosted dashboard.

---

Debugging agents is painful. You get a JSON trace dump, a failing run ID, and a vague sense that “something looped” or “the tool blew up.” Hosted observability tools help teams that already bought in, but they want accounts, network round-trips, and often a credit card. Your trace is on disk anyway.

**Agent Autopsy** is a small Python CLI that stays **local-first**: deterministic pattern detectors run first, optional LLM analysis runs second, and you never need a vendor login to see why a run failed.

## The approach

1. **Parse and normalize** common trace shapes (LangGraph, LangChain, generic JSON, experimental OpenTelemetry paths).
2. **Deterministic detectors** flag loops, retry storms, auth and timeout patterns, hallucinated tool names, context pressure, and more—before any model call.
3. **Optional LLM pass** for narrative synthesis, with streaming, disk cache, and **citation checks** so invented event IDs get flagged automatically.

That ordering matters: the fast path should answer “what broke?” in under a second on typical traces so you reach for `autopsy` before `grep`.

## One real bug it catches

Take a trace where the same tool is invoked with identical arguments dozens of times. Autopsy’s infinite-loop detector ties that to concrete **event IDs**, prints **evidence excerpts**, and suggests a **likely cause** (for example a missing router exit). You get a markdown report you can paste into an incident thread or attach to a PR—without uploading customer data to a third party.

## Try it

```bash
pip install agent-autopsy
autopsy analyze path/to/trace.json --no-llm
```

With API keys configured for your provider, drop `--no-llm` for streamed synthesis. **Ollama** works as a provider for fully local LLM runs.

Daily-driver commands that are hard in hosted UIs:

```bash
autopsy watch ./traces --pattern '*.json'
autopsy diff baseline.json regression.json -f json | jq .
autopsy replay trace.json --from 120 --speed 2
```

## Why local-first wins here

- **Privacy:** traces often contain prompts, PII-shaped strings, and internal tool payloads.  
- **Speed:** no upload step; cold path stays import-light (LangChain loads only on the LLM path).  
- **CI-friendly:** exit codes (`0` clean, `1` findings, `2` errors) and JSON output play nicely with scripts.

## What is next

Dogfood on real traces, keep detector precision/recall honest with the bundled corpus eval, and listen to issues from strangers. The maintainers are intentionally **not** building a SaaS replacement—see [ROADMAP.md](../ROADMAP.md) for scope boundaries.

If this sounds useful, star the repo, file an issue with a redacted trace snippet, or suggest one new pattern detector. The best roadmap is the one users write with bug reports.

---

Demo GIF (regenerate with `python scripts/render_demo_gif.py`): see [docs/images/autopsy-demo.gif](../docs/images/autopsy-demo.gif) and [demo-gif.md](demo-gif.md).
