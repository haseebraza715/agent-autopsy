# Demo Playbook

Use this script to demo Agent Autopsy in under 5 minutes.

## 1) Quick Summary

```bash
python -m src.cli summary examples/traces/loop_failure.json
```

Show:

- Run status
- Event/tool/error counts
- Framework/model metadata

## 2) Deterministic Analysis

```bash
python -m src.cli analyze examples/traces/loop_failure.json --no-llm -o /tmp/demo_report.md
```

Show:

- Pattern-driven diagnosis
- Timeline and health score
- Actionable fix recommendations

## 3) MCP Interface

```bash
python -m src.mcp --transport stdio
```

Show:

- MCP tools: `analyze_trace`, `detect_patterns`, `health_check`
- MCP resources: recent traces, pattern catalog
- MCP prompts: debug/health/compare/explain workflows

## 4) Compare Two Runs

Use MCP `compare_traces` or CLI summaries side-by-side to highlight improvements/regressions.
