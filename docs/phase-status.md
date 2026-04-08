# Implementation Status Tracker

Last updated: 2026-04-08

This file tracks roadmap execution from `docs/improvement-plan.md`.

## Phase Overview

| Phase | Status | Notes |
|---|---|---|
| Phase 1 - Clean Up What We Have | Completed | Implemented, tested, and committed |
| Phase 2 - Deepen the Core | Not Started | Pending after Phase 1 |
| Phase 3 - MCP Server Integration | Not Started | Pending |
| Phase 4 - Open Source Growth | Not Started | Pending |
| Phase 5 - Advanced Features | Not Started | Pending |

## Phase 1 - Clean Up What We Have

Status: Completed
Goal: Remove ghost features, fix tests, and improve reliability.

### TODO

- [x] Remove unused dependency (`sentence-transformers`) from `requirements.txt`
- [x] Make docs/README honest about LangChain/OpenTelemetry support status
- [x] Strengthen weak tests that cannot fail meaningfully
- [x] Add negative tests for clean traces
- [x] Add edge-case tests (empty trace, single event trace, large trace)
- [x] Replace bare `except:` blocks with specific exception handling
- [x] Add logging for swallowed/fallback errors
- [x] Improve Streamlit batch analysis error visibility
- [x] Add CI workflow to run tests on push/PR

### Completed in this phase

- [x] Created this status tracker with per-phase TODOs
- [x] Removed unused dependency and tightened version constraints in `requirements.txt`
- [x] Updated README/docs claims for parser support and fallback behavior
- [x] Rewrote pre-analysis tests with deterministic assertions and edge coverage
- [x] Strengthened ingestion tests with specific expected values and added parser coverage
- [x] Removed bare `except` blocks and added structured logging in app/scripts
- [x] Added GitHub Actions test workflow for push/PR validation

## Phase 2 - Deepen the Core

Status: Not Started
Goal: Improve analysis quality, parser depth, and deterministic report quality.

### TODO

- [ ] Strengthen LLM analysis agent with iteration budget and quality gate
- [ ] Build robust LangChain parser support
- [ ] Build robust OpenTelemetry parser support
- [ ] Add new pattern detectors (goal drift, stale context, token waste, auth failures, timeout, redundant calls)
- [ ] Improve deterministic narrative report output
- [ ] Make model context limits configurable

## Phase 3 - MCP Server Integration

Status: Not Started
Goal: Expose Agent Autopsy as MCP tools/resources/prompts.

### TODO

- [ ] Implement MCP server using official Python SDK
- [ ] Expose core tools (`analyze_trace`, `detect_patterns`, `validate_trace`, `get_trace_summary`, etc.)
- [ ] Expose MCP resources (recent traces, report archive, pattern catalog, config)
- [ ] Expose MCP prompt templates (debug my agent, quick health check, compare runs, explain failure)
- [ ] Support stdio and SSE/HTTP transports

## Phase 4 - Open Source Growth

Status: Not Started
Goal: Build contributor and adoption infrastructure.

### TODO

- [ ] Add `CONTRIBUTING.md`, issue templates, PR template
- [ ] Add `CHANGELOG.md` and `CODE_OF_CONDUCT.md`
- [ ] Overhaul user-facing docs and extension guides
- [ ] Package and publish to PyPI with optional dependency groups
- [ ] Add curated example traces and walkthroughs
- [ ] Improve project visibility and demo assets

## Phase 5 - Advanced Features

Status: Not Started
Goal: Add intelligent and extensible debugging capabilities.

### TODO

- [ ] Add semantic goal drift detection
- [ ] Add trace comparison and regression detection
- [ ] Add live trace monitoring with streaming alerts
- [ ] Add fix generation suggestions
- [ ] Add multi-agent trace support
- [ ] Add benchmark/evaluation mode
- [ ] Add plugin system for parsers, detectors, reports, and visualizations

## Change Log (Phase Execution)

- 2026-04-08: Initialized phase tracking file and seeded TODOs for all phases.
- 2026-04-08: Completed Phase 1 implementation (dependency cleanup, docs honesty, stronger tests, error handling/logging, CI workflow).
