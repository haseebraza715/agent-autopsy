#!/usr/bin/env bash
# Helper: commands to run inside `asciinema rec` for a README-quality terminal demo.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
echo "Run these inside asciinema (type 'exit' when done). Use a large font (e.g. 16–18pt) for HD GIF export."
echo ""
echo "  # Fast deterministic path"
echo "  autopsy analyze examples/traces/loop_failure.json --no-llm -q -f text | head -28"
echo ""
echo "  # Full path with LLM (needs OPENROUTER_API_KEY; can take ~1–2 min)"
echo "  autopsy analyze examples/traces/loop_failure.json -q -f text | head -80"
echo ""
echo "  autopsy summary examples/traces/successful_run.json"
echo "  exit"
echo ""
echo "Headless GIF (no asciinema): .venv/bin/python scripts/render_demo_gif.py"
echo "asciinema export: agg /tmp/autopsy-demo.cast docs/images/autopsy-demo.gif"
