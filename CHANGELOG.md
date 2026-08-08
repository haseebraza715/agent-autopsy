# Changelog

All notable changes to this project are documented in this file.

The format follows Keep a Changelog and semantic versioning intent.

## [Unreleased]

### Added

- Hand-labeled negative-control trace fixtures (`neg_*`) and positive-control fixtures for previously unrepresented detectors (`pos_*`: retry storm, goal drift, stale context, inter-agent failure)
- `must_not_include` support in the detector manifest and evaluator; per-pattern TP/FP/FN reporting with forbidden-detection enforcement

### Changed

- Deterministic detectors now require failure evidence: timeouts flag slow calls only on errored or failed runs and also recognize timeout language in failed assistant/tool evidence; loops and redundant-tool-call patterns require a failed run or errored events; empty-response skips successful tool outputs, including recovered calls with no remaining error summary
- CLI exit gate treats a recovered error with zero signals as a clean run
- Detector corpus metrics reframed as corpus-relative regression results (not external accuracy)
- Real-trace corpus under `tests/fixtures/real_traces/` with `scripts/eval_detectors.py` (CI gate)
- `autopsy watch`, `autopsy replay`, `autopsy diff` (alias of `compare`), richer trace diff output
- Deterministic report sections (what / where / evidence / likely cause) and `text` report format
- LLM disk cache (`~/.cache/agent-autopsy/`), optional `--stream` / `--no-cache` / `--provider` on `analyze`
- Structured JSON appendix for LLM synthesis with Pydantic validation (`src/analysis/structured_report.py`)
- Opt-in CLI telemetry (`autopsy telemetry on|off|status`, env `AUTOPSY_TELEMETRY=1`)
- Docs: `docs/launch-post.md`, `docs/demo-gif.md`, `docs/good-first-issues.md`, `ROADMAP.md`
- Scripts: `scripts/benchmark_no_llm.py`, `scripts/record_demo.sh`, `scripts/render_demo_gif.py` (README GIF)
- `docs/images/autopsy-demo.gif`: deterministic `autopsy analyze` demo asset
- PyPI publish workflow on version tags (`.github/workflows/publish.yml`)
- MCP server interface with tools, resources, and prompts (`src.mcp`)
- Streamable HTTP/SSE/stdio MCP transport support
- Advanced deterministic detectors and configurable model context limits
- Analysis quality gate with iterative report revision feedback
- Deterministic report health score and richer timeline rendering

### Changed

- LangGraph stack moved to `src/analysis/llm_agent.py` so `--no-llm` avoids importing LangChain
- CLI `analyze` defaults to `-f text`; exit code `2` for parse/tool errors
- `ReportGenerator` always surfaces deterministic markdown body in saved reports
- Parser depth improved for LangChain and OpenTelemetry traces
- Phase roadmap tracker updated through Phase 4

## [0.4.0] - 2026-04-09

### Added

- Phase 1, 2, and 3 roadmap deliverables
- CI workflow for pytest
- MCP docs and service-level tests

### Changed

- Improved docs around parser support and fallback behavior
- Improved error handling and logging visibility
