# Recording a README demo (GIF)

The v2 plan calls for a **~15s** terminal clip: paste a trace path → deterministic report → highlight a finding.

## Option 0: Regenerate from real CLI output (no asciinema)

The repo ships **`docs/images/autopsy-demo.gif`**, produced by:

```bash
.venv/bin/python scripts/render_demo_gif.py
```

That runs `autopsy analyze examples/traces/loop_failure.json --no-llm -q -f text` and animates the captured stdout with Pillow (dark terminal theme). Re-run after changing the example trace or CLI output format.

## Option A: asciinema + agg (sharp GIF)

1. Install [asciinema](https://asciinema.org/docs/installation) and [agg](https://github.com/asciinema/agg) (Rust) for GIF export.
2. From the repo root:

```bash
chmod +x scripts/record_demo.sh
./scripts/record_demo.sh   # prints the exact commands to copy-paste into asciinema rec
```

3. Record:

```bash
asciinema rec /tmp/autopsy-demo.cast
# inside the shell session, run the commands the script printed, then exit
```

4. Convert:

```bash
agg /tmp/autopsy-demo.cast docs/images/autopsy-demo.gif
```

5. In `README.md`, add below the hero line:

```markdown
![Demo](docs/images/autopsy-demo.gif)
```

Keep the GIF under ~2MB if possible (short session, small terminal font).

## Option B: ttygif / terminalizer

Any tool that emits a looping GIF is fine; prefer readable font size and **no** API keys in the recording.

## Scripted one-liner (no asciinema)

For quick validation without a GIF:

```bash
autopsy analyze examples/traces/loop_failure.json --no-llm -q -f text | head -40
```

Use this in CI smoke docs; use asciinema+agg for the marketing asset.
