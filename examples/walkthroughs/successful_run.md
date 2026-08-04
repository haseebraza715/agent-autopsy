# Walkthrough: Successful Run

Trace: `examples/traces/successful_run.json`

## Goal

Understand baseline behavior for a healthy trace.

## What to run

```bash
python -m agent_autopsy.cli summary examples/traces/successful_run.json
python -m agent_autopsy.cli analyze examples/traces/successful_run.json --no-llm -o /tmp/success_report.md
```

## Expected interpretation

- Status should be `success`.
- Error count should be `0`.
- Pattern detection should be minimal or empty.
- Health score should remain high.
