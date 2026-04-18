#!/usr/bin/env python3
"""
Render docs/images/autopsy-demo.gif from a real `autopsy analyze` run.

- Deterministic pre-analysis (always captured from CLI with --no-llm).
- LLM synthesis: uses live OpenRouter output when OPENROUTER_API_KEY is set
  (loads repo .env via python-dotenv); otherwise stitches the representative
  excerpt in scripts/demo_gif_llm_sample.txt.

Renders at 2x resolution then downsamples for sharper text (HD-style hero).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "images" / "autopsy-demo.gif"
TRACE = REPO / "examples" / "traces" / "loop_failure.json"
SAMPLE_LLM = REPO / "scripts" / "demo_gif_llm_sample.txt"


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(REPO / ".env", override=False)
    except Exception:
        pass


def _mono_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Menlo.ttc",
        "/System/Library/Fonts/Monaco.dfont",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/Library/Fonts/Menlo.ttc",
    ]
    for path in candidates:
        p = Path(path)
        if p.is_file():
            try:
                return ImageFont.truetype(str(p), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _wrap(raw: str, width: int) -> list[str]:
    if len(raw) <= width:
        return [raw]
    return textwrap.wrap(raw, width=width, break_long_words=True, replace_whitespace=False)


def _run_deterministic(max_lines: int) -> list[str]:
    env = {**os.environ, "PYTHONWARNINGS": "ignore", "NO_COLOR": "1"}
    cmd = [
        sys.executable,
        "-m",
        "src.cli",
        "analyze",
        str(TRACE),
        "--no-llm",
        "-q",
        "-f",
        "text",
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    body = (proc.stdout or "").strip()
    lines: list[str] = []
    for raw in body.splitlines():
        lines.extend(_wrap(raw, 92))
        if len(lines) >= max_lines:
            break
    return lines[:max_lines]


def _run_llm_live(max_lines: int, timeout: int) -> list[str] | None:
    if not (os.getenv("OPENROUTER_API_KEY") or "").strip():
        return None
    env = {**os.environ, "PYTHONWARNINGS": "ignore", "NO_COLOR": "1"}
    cmd = [
        sys.executable,
        "-m",
        "src.cli",
        "analyze",
        str(TRACE),
        "-q",
        "-f",
        "text",
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )
    if proc.returncode != 0:
        print(
            f"LLM analyze exited {proc.returncode}; stderr: {(proc.stderr or '')[:400]}",
            file=sys.stderr,
        )
        return None
    body = (proc.stdout or "").strip()
    lines: list[str] = []
    for raw in body.splitlines():
        lines.extend(_wrap(raw, 92))
    return _truncate_middle(lines, max_lines)


def _truncate_middle(lines: list[str], max_lines: int) -> list[str]:
    if len(lines) <= max_lines:
        return lines
    head = max_lines // 2
    tail = max_lines - head - 3
    return lines[:head] + ["", "  … truncated for demo …", ""] + lines[-tail:]


def _load_sample_llm() -> list[str]:
    raw = SAMPLE_LLM.read_text()
    lines: list[str] = []
    for ln in raw.splitlines():
        if not ln.strip():
            lines.append("")
        else:
            lines.extend(_wrap(ln.rstrip("\n"), 92))
    return lines


def _line_color(line: str) -> tuple[int, int, int]:
    s = line.lstrip()
    if line.startswith("$"):
        return (126, 231, 135)
    if s.startswith("##"):
        return (125, 211, 252)
    if "──" in line and "LLM" in line:
        return (210, 153, 99)
    if s.startswith("---") or s.startswith("──"):
        return (139, 148, 158)
    if s.startswith("- ") or s.startswith("* "):
        return (201, 209, 217)
    return (230, 237, 243)


def _draw_frame(
    lines: list[str],
    *,
    iw: int,
    ih: int,
    font: ImageFont.ImageFont,
    footer: str,
    pad: int,
    line_gap: int,
) -> Image.Image:
    bg = (11, 14, 20)
    img = Image.new("RGB", (iw, ih), bg)
    draw = ImageDraw.Draw(img)
    x0, y0 = pad, pad
    y = y0
    try:
        bbox = font.getbbox("Ay")
        lh = bbox[3] - bbox[1] + line_gap
    except Exception:
        lh = int(getattr(font, "size", 22) * 1.35) + line_gap

    for line in lines:
        if y + lh > ih - pad - lh * 2:
            draw.text((x0, y), "…", font=font, fill=(139, 148, 158))
            break
        draw.text((x0, y), line, font=font, fill=_line_color(line))
        y += lh

    small = _mono_font(max(18, getattr(font, "size", 44) // 2))
    draw.text((x0, ih - pad - 4), footer, font=small, fill=(110, 118, 129))
    return img


def main() -> int:
    parser = argparse.ArgumentParser(description="Render README demo GIF.")
    parser.add_argument(
        "--force-sample-llm",
        action="store_true",
        help="Never call OpenRouter; use scripts/demo_gif_llm_sample.txt for the synthesis block.",
    )
    parser.add_argument(
        "--no-live-llm",
        action="store_true",
        help="Skip live LLM even if OPENROUTER_API_KEY is set (use sample excerpt only).",
    )
    parser.add_argument(
        "--llm-timeout",
        type=int,
        default=150,
        help="Seconds to wait for live LLM analyze.",
    )
    args = parser.parse_args()
    _load_dotenv()

    det_max = 16
    det = _run_deterministic(det_max)

    used_live = False
    try_live = not args.force_sample_llm and not args.no_live_llm

    if args.force_sample_llm:
        llm_lines = _load_sample_llm()
    elif try_live:
        live = _run_llm_live(36, timeout=args.llm_timeout)
        if live:
            llm_lines = live
            used_live = True
        else:
            llm_lines = _load_sample_llm()
    else:
        llm_lines = _load_sample_llm()

    cmd_line = "$ autopsy analyze examples/traces/loop_failure.json -q -f text"
    script_lines: list[str] = [
        cmd_line,
        "",
        "── Deterministic pre-analysis ──",
        "",
        *det,
        "",
        "── LLM synthesis (markdown) ──",
        "",
        *llm_lines,
    ]

    max_script = 52
    if len(script_lines) > max_script:
        script_lines = script_lines[:max_script] + ["", "…"]

    if used_live:
        footer = "agent-autopsy · live OpenRouter + LangGraph (excerpt)"
    else:
        footer = (
            "agent-autopsy · HD demo — set OPENROUTER_API_KEY for live LLM capture in render_demo_gif.py"
        )

    # 2x supersample for crisp downscale (1600×900 hero)
    W, H = 1600, 900
    scale = 2
    iw, ih = W * scale, H * scale
    font = _mono_font(22 * scale)
    pad = 36 * scale
    line_gap = 6 * scale

    frames: list[Image.Image] = []
    for n in range(2, len(script_lines) + 1):
        chunk = script_lines[:n]
        big = _draw_frame(chunk, iw=iw, ih=ih, font=font, footer=footer, pad=pad, line_gap=line_gap)
        frames.append(big.resize((W, H), Image.Resampling.LANCZOS))

    if not frames:
        print("No frames generated", file=sys.stderr)
        return 2

    final = frames[-1]
    for _ in range(28):
        frames.append(final)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    duration_ms = 88
    frames[0].save(
        OUT,
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0,
        optimize=True,
    )
    mode = "live LLM" if used_live else "deterministic + sample LLM excerpt"
    print(f"Wrote {OUT} ({len(frames)} frames, {mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
