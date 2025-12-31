#!/usr/bin/env python3
"""
Verify and validate all traces.

Usage:
    python scripts/verify_traces.py [--traces-dir DIR]
"""

import argparse
import sys
from pathlib import Path

# Add scripts directory to path for module imports
scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir))

from modules.trace_verifier import TraceVerifier


def main():
    parser = argparse.ArgumentParser(
        description="Verify and validate all traces"
    )
    parser.add_argument(
        "--traces-dir",
        type=Path,
        default=Path("./traces"),
        help="Directory containing trace files (default: ./traces)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output"
    )
    
    args = parser.parse_args()
    
    verifier = TraceVerifier(traces_dir=args.traces_dir)
    result = verifier.verify_all(verbose=not args.quiet)
    
    return 0 if result.get("total_traces", 0) > 0 else 1


if __name__ == "__main__":
    exit(main())

