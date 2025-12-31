#!/usr/bin/env python3
"""
Analyze all traces and generate comprehensive reports.

Usage:
    python scripts/analyze_traces.py [--traces-dir DIR] [--reports-dir DIR]
"""

import argparse
from pathlib import Path

from modules.trace_analyzer import TraceAnalyzer
from modules.report_generator import SummaryReportGenerator


def main():
    parser = argparse.ArgumentParser(
        description="Analyze all traces and generate comprehensive reports"
    )
    parser.add_argument(
        "--traces-dir",
        type=Path,
        default=Path("./traces"),
        help="Directory containing trace files (default: ./traces)"
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=Path("./reports"),
        help="Directory to save reports (default: ./reports)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output"
    )
    
    args = parser.parse_args()
    
    # Analyze all traces
    analyzer = TraceAnalyzer(reports_dir=args.reports_dir)
    all_results = analyzer.analyze_all_traces(
        traces_dir=args.traces_dir,
        verbose=not args.quiet
    )
    
    # Generate summary report
    if not args.quiet:
        print("=" * 80)
        print("Generating summary report...")
        print("=" * 80)
        print()
    
    report_generator = SummaryReportGenerator(reports_dir=args.reports_dir)
    summary_file = report_generator.generate_summary(
        all_results=all_results,
        traces_dir=args.traces_dir,
        verbose=not args.quiet
    )
    
    if not args.quiet:
        print()
        successful = sum(1 for r in all_results if r["success"])
        total_patterns = sum(len(r.get("patterns", [])) for r in all_results)
        
        print("=" * 80)
        print("ANALYSIS COMPLETE")
        print("=" * 80)
        print()
        print(f"Total traces analyzed: {len(all_results)}")
        print(f"Successful analyses: {successful}")
        print(f"Total patterns detected: {total_patterns}")
        print(f"Summary report: {summary_file}")
        print()
    
    return 0 if all_results else 1


if __name__ == "__main__":
    exit(main())

