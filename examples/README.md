# Curated Examples

This folder contains starter traces and walkthroughs for evaluating Agent Autopsy quickly.

## Traces

- [`traces/successful_run.json`](traces/successful_run.json)
- [`traces/loop_failure.json`](traces/loop_failure.json)
- [`traces/loop_fixed.json`](traces/loop_fixed.json)
- [`traces/hallucinated_tool.json`](traces/hallucinated_tool.json)

`loop_failure.json` and `loop_fixed.json` are the same task before and after a
fix: run `autopsy diff` on them to see the failing-run patterns disappear.

## Walkthroughs

- [`walkthroughs/successful_run.md`](walkthroughs/successful_run.md)
- [`walkthroughs/loop_failure.md`](walkthroughs/loop_failure.md)
- [`walkthroughs/hallucinated_tool.md`](walkthroughs/hallucinated_tool.md)

## Try It

```bash
python -m agent_autopsy.cli summary examples/traces/loop_failure.json
python -m agent_autopsy.cli analyze examples/traces/loop_failure.json --no-llm -o /tmp/loop_report.md
python -m agent_autopsy.mcp --transport stdio
```
