#!/usr/bin/env bash
# Helper: commands to run inside `asciinema rec` for a short README demo.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
echo "Run these inside asciinema (type 'exit' when done):"
echo ""
echo "  autopsy analyze examples/traces/loop_failure.json --no-llm -q -f text | head -35"
echo "  autopsy summary examples/traces/successful_run.json"
echo "  exit"
echo ""
echo "Then: agg /tmp/autopsy-demo.cast docs/images/autopsy-demo.gif"
echo "(Install asciinema + agg; adjust cast path as you like.)"
