# Walkthrough: Hallucinated Tool

Trace: `examples/traces/hallucinated_tool.json`

## Goal

Validate tool-allowlist and contract-failure diagnostics.

## What to run

```bash
python -m src.cli summary examples/traces/hallucinated_tool.json
python -m src.cli analyze examples/traces/hallucinated_tool.json --no-llm -o /tmp/hallucinated_tool_report.md
```

## Expected interpretation

- Pattern output should include unknown/hallucinated tool usage.
- Suggested fixes should include stricter tool validation/guardrails.
- Evidence should cite specific event IDs where invalid tools are called.
