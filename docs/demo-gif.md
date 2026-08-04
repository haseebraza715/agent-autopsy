# Recording a README demo (GIF)

The hero asset **`docs/images/autopsy-demo.gif`** is generated at **1100×700** with **large monospace** (body ≈36px, title ≈52px) on a canvas matched to GitHub’s readme column width (~830px), so the preview barely downscales and type stays legible. It is a **20-second**, five-scene story designed for a 15–25 second demo slot.

## What the GIF shows

Structured in five quick beats:

1. A failed agent run and the one-command hook.
2. Local trace normalization and pattern checks.
3. Root cause: seven identical `web_search` calls and seven timeouts.
4. Trace-backed evidence: the same call repeated every two seconds without backoff.
5. The recommended fix: cap retries, add backoff, and stop retrying timeout failures.

The GIF is deterministic and uses facts from `examples/traces/loop_failure.json`; it does not require an API key.

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
