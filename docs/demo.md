# Demo Playbook

Use this script to demo Agent Autopsy in under 5 minutes.

For the README hero asset (video + GIF) and how to regenerate it, see the [README](../README.md) demo section.

## 1) Quick Summary

Use sample trace: [`examples/traces/loop_failure.json`](../examples/traces/loop_failure.json)

```bash
python -m agent_autopsy.cli summary examples/traces/loop_failure.json
```

Show:

- Run status
- Event/tool/error counts
- Framework/model metadata

## 2) Deterministic Analysis

Analyze the same trace: [`examples/traces/loop_failure.json`](../examples/traces/loop_failure.json)

```bash
python -m agent_autopsy.cli analyze examples/traces/loop_failure.json --no-llm -o /tmp/demo_report.md
```

Show:

- Pattern-driven diagnosis
- Timeline and health score
- Actionable fix recommendations

## 3) MCP Interface

```bash
python -m agent_autopsy.mcp --transport stdio
```

Show:

- MCP tools: `analyze_trace`, `detect_patterns`, `health_check`
- MCP resources: recent traces, pattern catalog
- MCP prompts: debug/health/compare/explain workflows

## 4) Compare Two Runs

Use MCP `compare_traces` or CLI summaries side-by-side to highlight improvements/regressions.
