#!/usr/bin/env python3
"""
Cold-path benchmark: load trace + preanalysis + deterministic report (no LLM).

Usage:
  python scripts/benchmark_no_llm.py path/to/trace.json
  python scripts/benchmark_no_llm.py path/to/trace.json --repeat 5
"""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import api


def once(path: Path) -> float:
    t0 = time.perf_counter()
    trace = api.load_trace(path)
    api.apply_embedding_defaults_for_trace(trace)
    api.run_preanalysis(trace)
    api.run_deterministic_analysis(trace)
    return time.perf_counter() - t0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("trace", type=Path, help="Trace JSON file")
    ap.add_argument("--repeat", type=int, default=1, help="Repeat count (warm disk cache)")
    args = ap.parse_args()
    if not args.trace.is_file():
        print(f"Not a file: {args.trace}", file=sys.stderr)
        return 2
    times = [once(args.trace) for _ in range(max(1, args.repeat))]
    ms = [t * 1000 for t in times]
    print(f"runs={len(ms)} min={min(ms):.1f}ms max={max(ms):.1f}ms mean={statistics.mean(ms):.1f}ms")
    if len(ms) > 1:
        print(f"stdev={statistics.stdev(ms):.1f}ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
