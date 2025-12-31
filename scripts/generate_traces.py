#!/usr/bin/env python3
"""
Generate traces by running the analysis agent multiple times.

Usage:
    python scripts/generate_traces.py [--min-runs N] [--stop-on-failure]
"""

import argparse
from pathlib import Path

from modules.trace_generator import TraceGenerator


def main():
    parser = argparse.ArgumentParser(
        description="Generate traces by running analysis agent multiple times"
    )
    parser.add_argument(
        "--min-runs",
        type=int,
        default=20,
        help="Minimum number of runs before stopping (default: 20)"
    )
    parser.add_argument(
        "--stop-on-failure",
        action="store_true",
        help="Stop after finding a failure (if min_runs reached)"
    )
    parser.add_argument(
        "--traces-dir",
        type=Path,
        default=Path("./traces"),
        help="Directory to save traces (default: ./traces)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output"
    )
    
    args = parser.parse_args()
    
    # Sample trace files
    sample_traces = [
        "tests/sample_traces/successful_run.json",
        "tests/sample_traces/loop_failure.json",
        "tests/sample_traces/hallucinated_tool.json",
    ]
    
    generator = TraceGenerator(traces_dir=args.traces_dir)
    result = generator.generate_traces(
        sample_traces=sample_traces,
        min_runs=args.min_runs,
        stop_on_failure=args.stop_on_failure,
        verbose=not args.quiet
    )
    
    return 0 if result["new_traces"] > 0 else 1


if __name__ == "__main__":
    exit(main())

