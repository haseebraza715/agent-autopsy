#!/usr/bin/env python3
"""
Evaluate PatternDetector against tests/fixtures/real_traces/_manifest.yaml.

Exit 1 if recall or precision falls below thresholds (defaults: 80% / 90%).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_autopsy.ingestion import TraceNormalizer, parse_trace_file
from agent_autopsy.preanalysis import PatternDetector
from agent_autopsy.utils.config import get_config


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
    ap.add_argument("--json-out", type=Path, default=None)
    args = ap.parse_args()

    manifest_path = args.corpus / "_manifest.yaml"
    if not manifest_path.is_file():
        print(f"Missing manifest: {manifest_path}", file=sys.stderr)
        return 2

    manifest = load_manifest(manifest_path)
    entries = manifest.get("entries", [])

    # The labeled evaluator intentionally uses the deterministic lexical drift
    # fallback. Detector corpus metrics must never depend on a remote model.
    get_config().skip_embeddings = True

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
    metrics: dict[str, dict[str, float | int]] = {"recall": {}, "precision": {}}

    for p in sorted(recall_hits.keys()):
        hits = recall_hits[p]
        rec = sum(hits) / len(hits) if hits else 1.0
        lines.append(f"Recall {p}: {rec:.1%} ({sum(hits)}/{len(hits)})")
        metrics["recall"][p] = {"rate": rec, "hits": sum(hits), "total": len(hits)}
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
        metrics["precision"][p] = {"rate": prec, "tp": tp, "fp": fp}
        if denom and prec < args.min_precision:
            failures.append(f"Precision {p} {prec:.1%} < {args.min_precision:.0%}")

    print("\n".join(lines))

    if args.json_out is not None:
        digest = hashlib.sha256()
        for path in sorted(p for p in args.corpus.rglob("*") if p.is_file()):
            digest.update(path.relative_to(args.corpus).as_posix().encode())
            digest.update(path.read_bytes())
        try:
            commit = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
                capture_output=True, text=True,
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            commit = "unknown"
        payload = {
            "command": "python scripts/eval_detectors.py --json-out docs/evidence/detector-eval.json",
            "corpus_sha256": digest.hexdigest(),
            "commit": commit,
            "embedding_backend": "lexical_overlap_deterministic",
            "thresholds": {"min_recall": args.min_recall, "min_precision": args.min_precision},
            "metrics": metrics,
            "passed": not failures,
        }
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    if failures:
        print("\nFAILED:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print("\nOK — all per-pattern metrics meet thresholds.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
