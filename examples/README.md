# Curated Examples

This folder contains starter traces and walkthroughs for evaluating Agent Autopsy quickly.

## Traces

- `traces/successful_run.json`
- `traces/loop_failure.json`
- `traces/hallucinated_tool.json`

## Walkthroughs

- `walkthroughs/successful_run.md`
- `walkthroughs/loop_failure.md`
- `walkthroughs/hallucinated_tool.md`

## Try It

```bash
python -m src.cli summary examples/traces/loop_failure.json
python -m src.cli analyze examples/traces/loop_failure.json --no-llm -o /tmp/loop_report.md
python -m src.mcp --transport stdio
```
