# Agent Autopsy — Portfolio Summary

Deterministic, fully offline forensics for AI-agent traces: find loops, retry storms, and hallucinations without an LLM.

## CV bullets

- **Built a local-first agent-debugging CLI** (Python, 278 tests, CI-gated) that ingests LangGraph/LangChain/OpenTelemetry/generic JSON traces into one normalized event model, then runs 13+ deterministic failure detectors (infinite loops, retry storms, error cascades, hallucinated tool calls) that report findings with trace evidence and a health score.
- **Solved the reproducibility problem**: analysis is deterministic-first and runs with zero network and zero API keys — detectors are pure functions over the event stream, the CLI falls back to deterministic mode when no LLM credential exists, and a labeled corpus in CI (`scripts/eval_detectors.py`) prevents detector regressions.
- **Designed a gatable CLI contract** — exit codes `0` clean / `1` findings / `2` error — so teams can fail CI on a broken agent run, plus `diff` to prove a fix changed behavior (failing vs. fixed trace), patch-artifact generation, an MCP server, and a Streamlit UI sharing one `api.py` facade.

## 15-second explanation

Agent traces are messy JSON dumps; when a run fails, you usually read logs by hand or upload them to a hosted dashboard. Agent Autopsy is a CLI that takes the trace file and, fully offline with no API keys, normalizes it into one event model, runs deterministic pattern detectors (loops, retry storms, error cascades, hallucinated tools), and prints a report with evidence and a health score. It exits `0` on clean runs and `1` when findings are detected, so CI can gate on it.

## 45-second explanation

The core problem: LLM-agent failures are non-deterministic and traces are format-heterogeneous, so debugging is ad-hoc and hard to automate. Agent Autopsy is engineered to make failure analysis deterministic and local. Ingestion auto-detects four trace formats and normalizes everything into a single event schema, so all downstream logic — detectors, reports, diffs — sees the same model. The detection layer is 13+ pure-function pattern detectors plus static tool-contract validation (allow-list checking for hallucinated tool calls), each emitting findings with cited event IDs and trace excerpts. The report layer adds a health score and fix suggestions. The CLI gate (exit 1 on findings) makes it usable as a CI step; `autopsy diff` isolates exactly which patterns a fix removed by comparing failing vs. fixed runs. The default path never touches the network — LLM root-cause narratives are opt-in and fall back to deterministic mode without a key. The whole thing is verified by 278 tests and a labeled detector corpus that runs in CI with ruff.

## Five questions a staff engineer might ask

**Q1. How do you know your deterministic detectors aren't just garbage in, garbage out?**
The detector thresholds are validated against a labeled corpus of positive and negative control traces (`tests/fixtures/real_traces/`, evaluated by `scripts/eval_detectors.py`), which runs in CI with `HF_HUB_OFFLINE=1` so it never silently downloads data. The corpus includes `must_not_include` constraints — patterns that must *not* fire on a given trace — and every detector change is gated on corpus precision. The trade-off is documented honestly in the README: detectors are heuristics, so a quiet failure can still slip through, and precision-focused tuning can miss edge cases until a new labeled fixture is added.

**Q2. Why did you normalize four formats into one event model instead of handling them separately?**
Because every downstream feature — detectors, reports, diff, MCP tools, the Streamlit UI — should see the same structure, and new parsers should be pluggable without touching detection logic. The `Trace`/`Event` schema is the contract; format sniffing lives in `ingestion/parser.py` behind a plugin interface. The cost is that the normalized model can lose format-specific fidelity, which is listed as a limitation, and the generic JSON fallback accepts that loss.

**Q3. What makes the analysis "deterministic" when LLMs are involved?**
Determinism applies to the core path: detection is pure functions over the event stream — same trace in, same findings out, always offline, no model temperature involved. The LLM is an optional layer for root-cause *narrative*, not detection: it reads the normalized trace, its output is scored by a `ReportQualityValidator`, and it can be revised up to a bounded number of times within a token budget. If no API key is configured, or the LLM call fails, the CLI silently falls back to the deterministic report — so a paid-service outage never blocks a diagnosis. Goal-drift is the one detector with an optional embedding model, and it falls back to lexical overlap when embeddings are disabled.

**Q4. How do you handle the time dimension — e.g., retry storms — without false positives on legitimate repeated calls?**
Retry-storm detection clusters same-tool calls with a *chained* time window (`preanalysis/patterns.py:detect_retry_storms`): each candidate event must fall within the window of the last event already in the cluster, rather than a fixed anchor, so a long chain of retries is caught as one storm instead of being split below threshold. It also excludes event IDs already claimed by the infinite-loop detector to avoid double-reporting. Loop detection requires a failed run or errored events before it fires — a recovered error with zero signals exits clean (see `cli.py:_trace_has_findings`).

**Q5. What does "CI-gateable" actually mean here, and how is it tested?**
The CLI contract is exit code 0 = no actionable findings, 1 = findings, 2 = tool/parse error. `_trace_has_findings` is explicit: it fires on detected signals, on a non-success status, or on a failed run with an error summary — but a recovered error with zero signals exits 0. That exact decision table is covered by tests (`tests/test_cli.py`) and exercised by the demo (analyzing the hallucinated-tool trace exits 1). The workflow (`tests.yml`) runs the suite on Python 3.10/3.11/3.12 plus ruff and the corpus eval, so the gate itself is what ships.
