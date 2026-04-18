# Recording a README demo (GIF)

The hero asset **`docs/images/autopsy-demo.gif`** is generated at **1920×1080** with **extra-large monospace** (body ≈56px, title ≈72px, command ≈50px) and short wrapped lines so GitHub’s scaled-down preview stays readable. There is **no downscale** of the canvas; only a few CLI lines are shown so type can stay huge.

## What the GIF shows

Structured in two clear steps:

1. **Step 1 — Deterministic** — real output from  
   `autopsy analyze examples/traces/loop_failure.json --no-llm -q -f text` (trimmed for length)
2. **Step 2 — LLM synthesis** — either:
   - **Live** OpenRouter + LangGraph output when `OPENROUTER_API_KEY` is set (repo `.env` is loaded automatically), or  
   - A **representative excerpt** from `scripts/demo_gif_llm_sample.txt` if the key is missing or the live run fails.

The command line in the GIF is the full path (with LLM):  
`autopsy analyze examples/traces/loop_failure.json -q -f text`

## Regenerate (recommended)

```bash
.venv/bin/python scripts/render_demo_gif.py
```

Optional flags:

| Flag | Meaning |
|------|--------|
| `--force-sample-llm` | Never call the API; always use `demo_gif_llm_sample.txt` (CI-friendly). |
| `--no-live-llm` | Same as above when you have a key but want the canned excerpt. |
| `--llm-timeout N` | Seconds to wait for live analyze (default 150). |

**Live capture** needs a valid OpenRouter model id in `DEFAULT_MODEL` and a working key. If the provider returns 400, the script falls back to the sample excerpt and still writes the GIF.

## Option A: asciinema + agg (alternative)

1. Install [asciinema](https://asciinema.org/docs/installation) and [agg](https://github.com/asciinema/agg).
2. `./scripts/record_demo.sh` — prints commands to paste into `asciinema rec`.
3. `agg /tmp/autopsy-demo.cast docs/images/autopsy-demo.gif` — use a large terminal font for a crisp export.

Keep the GIF roughly under **2–3 MB** for README load times (short session, moderate frame count).

## Quick text-only smoke (no GIF)

```bash
autopsy analyze examples/traces/loop_failure.json --no-llm -q -f text | head -40
```
