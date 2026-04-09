# Extension Guide

This guide covers how to extend Agent Autopsy safely.

## Add a New Trace Parser

1. Create a parser in `src/ingestion/formats/`.
2. Implement:
   - `can_parse(data: dict) -> bool`
   - `parse(data: dict) -> Trace`
3. Register parser selection logic in `TraceParser.detect_format`.
4. Add ingestion tests in `tests/test_ingestion.py`.

Checklist:

- Normalize to `Trace`/`TraceEvent` schema.
- Preserve parent-child event relationships.
- Extract model/tool metadata when available.
- Parse token and latency metadata where possible.

## Add a New Pattern Detector

1. Add enum value in `PatternType` (`src/preanalysis/patterns.py`).
2. Implement `detect_*` method in `PatternDetector`.
3. Wire method into `detect_all()`.
4. Add/update hypotheses in `RootCauseBuilder` (`src/preanalysis/suspects.py`).
5. Add deterministic tests in `tests/test_preanalysis.py`.

Checklist:

- Avoid high false-positive heuristics.
- Include evidence and event IDs.
- Set severity carefully.
- Keep detector deterministic and cheap.

## Extend Reporting

1. Update report extraction/rendering in `src/output/report.py`.
2. Keep markdown and JSON outputs aligned.
3. Add tests in `tests/test_report.py`.

Checklist:

- Keep sections stable for downstream consumers.
- Preserve event evidence references.
- Avoid LLM-only assumptions in deterministic mode.

## Extend MCP Interface

1. Add pure service logic in `src/mcp/service.py`.
2. Expose tool/resource/prompt in `src/mcp/server.py`.
3. Add service tests in `tests/test_mcp_service.py`.
4. Document changes in `docs/mcp.md`.

Checklist:

- Accept both file path and inline JSON when relevant.
- Return structured JSON payloads.
- Keep tool behavior deterministic where possible.
- Validate failure mode and error messages.
