# Changelog

All notable changes to this project are documented in this file.

The format follows Keep a Changelog and semantic versioning intent.

## [Unreleased]

### Added

- MCP server interface with tools, resources, and prompts (`src.mcp`)
- Streamable HTTP/SSE/stdio MCP transport support
- Advanced deterministic detectors and configurable model context limits
- Analysis quality gate with iterative report revision feedback
- Deterministic report health score and richer timeline rendering

### Changed

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
