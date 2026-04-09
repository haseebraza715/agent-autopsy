# Walkthrough: Loop Failure

Trace: `examples/traces/loop_failure.json`

## Goal

See how loop and retry-related failures are surfaced.

## What to run

```bash
python -m src.cli summary examples/traces/loop_failure.json
python -m src.cli analyze examples/traces/loop_failure.json --no-llm -o /tmp/loop_report.md
```

## Expected interpretation

- Status should be `failed`.
- Pattern output should include loop and/or retry-like behavior.
- Fix recommendations should include iteration guards and retry control.
- Health score should be significantly lower than a successful run.
