# Agent Autopsy article fact-check

This file maps the article's important technical claims to the current repository state and the verification run performed on 2026-07-16.

| Article claim | Evidence |
|---|---|
| Accepts generic JSON, LangGraph, LangChain, and OpenTelemetry trace shapes, with plugin parsers checked first | `src/agent_autopsy/ingestion/parser.py:37-75`, `src/agent_autopsy/ingestion/parser.py:131-167`, `tests/test_ingestion.py` |
| Normalizes into `Trace`, `TraceEvent`, task, environment, and stats models | `src/agent_autopsy/schema/trace_v2.py:52`, `src/agent_autopsy/schema/trace_v2.py:105`, `src/agent_autopsy/schema/trace_v2.py:117`, `src/agent_autopsy/schema/trace_v2.py:130`, `src/agent_autopsy/schema/trace_v2.py:155` |
| Normalization preserves parser order, renumbers events, remaps parents, fills timestamps, and recalculates stats | `src/agent_autopsy/ingestion/normalizer.py:15-46`, `src/agent_autopsy/ingestion/normalizer.py:49-92`; there is no sort in `normalize` |
| Runs 13 built-in deterministic pattern detector methods | `src/agent_autopsy/preanalysis/patterns.py:82-106`; method implementations begin at lines 112, 162, 226, 261, 292, 329, 356, 383, 418, 463, 489, 529, and 561 |
| Tool contract validation is a separate pass | `src/agent_autopsy/preanalysis/contracts.py:34-153`, `src/agent_autopsy/preanalysis/suspects.py:81-95` |
| Hypotheses use fixed confidence templates and are sorted descending | `src/agent_autopsy/preanalysis/suspects.py:95`, confidence assignments at `src/agent_autopsy/preanalysis/suspects.py:158-448` |
| Deterministic reports label likely causes as heuristic | `src/agent_autopsy/output/deterministic_report.py:12-46`, `src/agent_autopsy/output/deterministic_report.py:86-133` |
| Optional LLM analysis follows pre-analysis and has deterministic fallback | `src/agent_autopsy/api.py:83-148`, `src/agent_autopsy/api.py:153-188`, `src/agent_autopsy/analysis/citation_validate.py`, `src/agent_autopsy/analysis/structured_report.py` |
| Reports expose timelines, root causes, fixes, confidence, health score, Markdown, and JSON | `src/agent_autopsy/output/report.py:46-360` |
| Retry fixture has 10 events: event 0 planning, events 1-8 identical failing `health_check` calls, event 9 max-retry termination | `tests/fixtures/real_traces/fail_retrystorm_b8f735cd.json:1-154` |
| Exact retry input is payment service plus a 1000 ms timeout, and every attempt returns connection refused | `tests/fixtures/real_traces/fail_retrystorm_b8f735cd.json:19-137` |
| The retry fixture emits `infinite_loop` rather than `retry_storm`, plus `empty_response` and `error_cascade` | CLI command below; expected baseline in `tests/fixtures/real_traces/_manifest.yaml:19-20`; loop suppression in `src/agent_autopsy/preanalysis/patterns.py:175-218` |
| Default identical-loop threshold is three | `src/agent_autopsy/preanalysis/patterns.py:112` |
| Retry CLI output reports critical loop events 1-8, high cascade events 1-9, medium empty responses 1-8, 85% top template confidence, and health score 34 | `.venv/bin/autopsy analyze tests/fixtures/real_traces/fail_retrystorm_b8f735cd.json --no-llm --no-embeddings --quiet --format json` |
| Focused demo uses the real parser and pre-analysis, then presents three or more identical failed calls as “Retry Storm” | `src/agent_autopsy/ui/demo_page.py:101-141`, `src/agent_autopsy/ui/demo_page.py:333-338`, `tests/test_demo_ui.py:11-22` |
| Visible demo Event 2 maps to internal event ID 1 | `src/agent_autopsy/ui/demo_page.py:73-78`, `src/agent_autopsy/ui/demo_page.py:260-292`, `tests/test_demo_ui.py:18` |
| Project exposes CLI, Streamlit, MCP, and Python API surfaces | `pyproject.toml` project scripts; `src/agent_autopsy/cli.py:50-900`; `app.py`; `pages/`; `src/agent_autopsy/mcp/server.py:69-259`; `src/agent_autopsy/api.py` |
| Test suite passed 122 tests | `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python -m pytest -q` → `122 passed, 1 warning in 16.77s` |
| Ruff passed | `python3 -m ruff check src scripts tests` → `All checks passed!` |
| All 21 corpus JSON traces completed deterministic batch analysis with 38 total signals | `OPENROUTER_API_KEY= OPENAI_API_KEY= ANTHROPIC_API_KEY= PROVIDER=openrouter AUTOPSY_NO_EMBEDDINGS=1 .venv/bin/python scripts/analyze_traces.py --traces-dir tests/fixtures/real_traces --reports-dir /tmp/agent-autopsy-article-reports-migrated --quiet`; summary reported 21 analyzed, 21 successful analyses, 38 signals |
| All three public examples completed deterministic batch analysis with nine total signals | Same batch command with `--traces-dir examples/traces --reports-dir /tmp/agent-autopsy-example-reports-migrated`; summary reported 3 analyzed, 3 successful analyses, 9 signals |
| Detector evaluator met thresholds across the represented patterns | `.venv/bin/python scripts/eval_detectors.py --json-out docs/evidence/detector-eval.json`; per-pattern TP/FP/FN with 100% precision/recall on the hand-labeled corpus; evaluator implementation in `scripts/eval_detectors.py` |
| Corpus results are regression checks, not an external benchmark | Manifest is hand-specified per scenario (`tests/fixtures/real_traces/_manifest.yaml`), includes five `must_not_include` negative controls, four `clean` traces, and one excluded unlabeled failure entry (`fail_notfound`, `skip_eval: true`); no external benchmark dataset is present |
| Screenshot is from the working focused demo after clicking Analyze Run | `pages/demo.py`, `src/agent_autopsy/ui/demo_page.py`; browser verification showed the selected retry trace, 10 loaded events, critical finding, rendered events 1-10, root-cause text, and three fixes |

## verification notes and limits

- The virtual environment used Python 3.12.13 and `pip check` reported no broken requirements.
- The test warning is a LangChain pending deprecation warning originating from the installed `langgraph` dependency.
- The CLI retry analysis exits with code 1 by design because actionable findings were detected. Parse or tool errors use exit code 2.
- The detector evaluator's perfect fixture result must not be described as detector accuracy on unseen data; it is a corpus-relative regression check over a hand-labeled, repo-local corpus.
- No remote OpenRouter, OpenAI, Anthropic, or Ollama model call was exercised in this verification pass.
- No production usage, user count, prevention rate, or independent detector-accuracy claim was found or made.
- The exact X demo URL was not present, so the article retains `Demo: [insert X demo link]`.
