#!/usr/bin/env python3
"""
Evaluate PatternDetector against tests/fixtures/real_traces/_manifest.yaml.

Exit 1 if recall or precision falls below thresholds (defaults: 80% / 90%).
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ingestion import TraceNormalizer, parse_trace_file
from src.preanalysis import PatternDetector


def load_manifest(path: Path) -> dict:
    data = yaml.safe_load(path.read_text())
    return data


def detect_patterns_for_file(corpus_dir: Path, filename: str) -> set[str]:
    path = corpus_dir / filename
    trace = TraceNormalizer.normalize(parse_trace_file(path))
    return {p.pattern_type.value for p in PatternDetector(trace).detect_all()}


def main() -> int:
    ap = argparse.ArgumentParser(description="Detector precision/recall eval")
    ap.add_argument(
        "--corpus",
        type=Path,
        default=ROOT / "tests/fixtures/real_traces",
        help="Directory containing traces and _manifest.yaml",
    )
    ap.add_argument("--min-recall", type=float, default=0.80)
    ap.add_argument("--min-precision", type=float, default=0.90)
    args = ap.parse_args()

    manifest_path = args.corpus / "_manifest.yaml"
    if not manifest_path.is_file():
        print(f"Missing manifest: {manifest_path}", file=sys.stderr)
        return 2

    manifest = load_manifest(manifest_path)
    entries = manifest.get("entries", [])

    # Per-pattern recall: expected hits vs satisfied
    recall_hits: dict[str, list[bool]] = defaultdict(list)
    # Per-pattern precision: (tp, fp) counts
    precision_tp: dict[str, int] = defaultdict(int)
    precision_fp: dict[str, int] = defaultdict(int)

    for entry in entries:
        if entry.get("skip_eval"):
            continue
        fname = entry["file"]
        detected = detect_patterns_for_file(args.corpus, fname)
        must = set(entry.get("must_include") or [])
        clean = bool(entry.get("clean"))

        if clean:
            for p in detected:
                precision_fp[p] += 1
            continue

        for p in must:
            recall_hits[p].append(p in detected)

        for p in detected:
            if p in must:
                precision_tp[p] += 1
            else:
                precision_fp[p] += 1

    failures: list[str] = []
    lines: list[str] = ["Pattern detector eval", "=====================", ""]

    for p in sorted(recall_hits.keys()):
        hits = recall_hits[p]
        rec = sum(hits) / len(hits) if hits else 1.0
        lines.append(f"Recall {p}: {rec:.1%} ({sum(hits)}/{len(hits)})")
        if hits and rec < args.min_recall:
            failures.append(f"Recall {p} {rec:.1%} < {args.min_recall:.0%}")

    lines.append("")

    all_patterns = sorted(set(precision_tp.keys()) | set(precision_fp.keys()))
    for p in all_patterns:
        tp = precision_tp[p]
        fp = precision_fp[p]
        denom = tp + fp
        prec = tp / denom if denom else 1.0
        lines.append(f"Precision {p}: {prec:.1%} (tp={tp}, fp={fp})")
        if denom and prec < args.min_precision:
            failures.append(f"Precision {p} {prec:.1%} < {args.min_precision:.0%}")

    print("\n".join(lines))

    if failures:
        print("\nFAILED:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print("\nOK — all per-pattern metrics meet thresholds.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
