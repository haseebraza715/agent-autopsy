#!/usr/bin/env python3
"""
Evaluate PatternDetector against tests/fixtures/real_traces/_manifest.yaml.

The manifest is HAND-LABELED per scenario intent, not derived from detector
output. Entries declare must_include (positive controls), must_not_include
(negative controls), or clean (no patterns). The evaluator reports per-pattern
TP/FP/FN, precision, and recall, and:

- exits 1 if any must_not_include pattern is detected (forbidden detection), or
- exits 1 if per-pattern precision or recall falls below thresholds.

Reported numbers are corpus-relative regression results, not a measure of
detector accuracy on unseen production traces.
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
    # fallback. Corpus metrics must never depend on a remote model.
    get_config().skip_embeddings = True

    # Per-pattern counts across all labeled entries.
    tp: dict[str, int] = defaultdict(int)
    fp: dict[str, int] = defaultdict(int)
    fn: dict[str, int] = defaultdict(int)
    forbidden: list[tuple[str, str]] = []  # (filename, pattern) violations

    for entry in entries:
        if entry.get("skip_eval"):
            continue
        fname = entry["file"]
        detected = detect_patterns_for_file(args.corpus, fname)
        must = set(entry.get("must_include") or [])
        must_not = set(entry.get("must_not_include") or [])
        clean = bool(entry.get("clean"))

        if clean:
            for p in detected:
                fp[p] += 1
            continue

        if not must and not must_not:
            # Unlabeled failure entry (e.g. a failure class with no detector):
            # any detection is a false positive.
            for p in detected:
                fp[p] += 1
            continue

        for p in must:
            if p in detected:
                tp[p] += 1
            else:
                fn[p] += 1

        for p in detected:
            if p in must:
                continue
            fp[p] += 1
            if p in must_not:
                forbidden.append((fname, p))

    failures: list[str] = []
    lines: list[str] = [
        "Pattern detector eval (hand-labeled corpus)",
        "===========================================",
        "",
    ]
    metrics: dict[str, dict[str, object]] = {"recall": {}, "precision": {}}

    all_patterns = sorted(set(tp.keys()) | set(fp.keys()) | set(fn.keys()))
    total_tp = total_fp = total_fn = 0

    lines.append("Per-pattern recall (positive controls)")
    for p in sorted({x for m in (tp, fp, fn) for x in m}):
        t, f = tp[p], fn[p]
        total_tp += t
        total_fn += f
        if t + f == 0:
            lines.append(f"  Recall {p}: n/a (0 positive cases)")
            metrics["recall"][p] = {"rate": None, "tp": t, "fn": f}
            continue
        rec = t / (t + f)
        lines.append(f"  Recall {p}: {rec:.1%} (tp={t}, fn={f})")
        metrics["recall"][p] = {"rate": rec, "tp": t, "fn": f}
        if rec < args.min_recall:
            failures.append(f"Recall {p} {rec:.1%} < {args.min_recall:.0%}")

    lines.append("")
    lines.append("Per-pattern precision (positive + negative controls)")
    for p in all_patterns:
        t, f = tp[p], fp[p]
        total_fp += f
        denom = t + f
        if denom == 0:
            lines.append(f"  Precision {p}: n/a (0 cases)")
            metrics["precision"][p] = {"rate": None, "tp": t, "fp": f}
            continue
        prec = t / denom
        lines.append(f"  Precision {p}: {prec:.1%} (tp={t}, fp={f})")
        metrics["precision"][p] = {"rate": prec, "tp": t, "fp": f}
        if prec < args.min_precision:
            failures.append(f"Precision {p} {prec:.1%} < {args.min_precision:.0%}")

    lines.append("")
    overall_rec = total_tp / (total_tp + total_fn) if total_tp + total_fn else None
    overall_prec = total_tp / (total_tp + total_fp) if total_tp + total_fp else None
    lines.append(
        "Overall: "
        + (
            f"recall={overall_rec:.1%} precision={overall_prec:.1%} (tp={total_tp}, fp={total_fp}, fn={total_fn})"
            if overall_prec is not None
            else "no labeled cases"
        )
    )

    if forbidden:
        lines.append("")
        lines.append("FORBIDDEN DETECTIONS (must_not_include violated):")
        for fname, p in forbidden:
            lines.append(f"  - {fname}: detected {p}")
            failures.append(f"Forbidden detection {p} in {fname}")

    print("\n".join(lines))

    if args.json_out is not None:
        digest = hashlib.sha256()
        for path in sorted(p for p in args.corpus.rglob("*") if p.is_file()):
            digest.update(path.relative_to(args.corpus).as_posix().encode())
            digest.update(path.read_bytes())
        try:
            commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            commit = "unknown"
        payload = {
            "command": "python scripts/eval_detectors.py --json-out docs/evidence/detector-eval.json",
            "corpus_sha256": digest.hexdigest(),
            "commit": commit,
            "embedding_backend": "lexical_overlap_deterministic",
            "scope": "corpus-relative regression results; not accuracy on unseen production traces",
            "thresholds": {"min_recall": args.min_recall, "min_precision": args.min_precision},
            "metrics": metrics,
            "totals": {"tp": total_tp, "fp": total_fp, "fn": total_fn},
            "forbidden_detections": forbidden,
            "passed": not failures,
        }
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    if failures:
        print("\nFAILED:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print("\nOK — no forbidden detections; all per-pattern metrics meet thresholds.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
