# Roadmap (post-v2 plan)

This file tracks **suggested** follow-ups from launch feedback and internal dogfooding. Nothing here is committed until prioritized in an issue or milestone.

## Near term

- **Detector tuning:** Expand `fail_notfound`-style cases in the corpus once labels exist; tighten `empty_response` heuristics if false positives appear in the wild.
- **Performance:** Hold the under-one-second no-LLM budget on a 10MB trace using `scripts/benchmark_no_llm.py` in CI (threshold job) once a stable large fixture is checked in.
- **CLI size:** Split `src/cli.py` into `cli_analyze.py` / `cli_watch.py` when it grows past maintainability.
- **Structured LLM:** Optional `--structured-only` mode that rejects reports missing a valid JSON fence.

## Medium term

- **Streamlit:** Reuse `stream_llm_analysis_text` with clearer step labels (“calling get_event…”) aligned with CLI `--stream`.
- **More trace formats:** Only when a real user issue justifies it (per project principles).

## Explicitly not planned (v2 principles)

- Hosted SaaS replacing local-first workflows  
- VS Code extension (maybe v3)  
- Plugin marketplace before multiple community plugins exist  
- LLM chat UI over a trace (scope creep)

## How to propose work

Open a GitHub issue with problem statement, trace sample (or public link), and expected CLI/report behavior. See [docs/good-first-issues.md](docs/good-first-issues.md) for starter ideas.
