#!/usr/bin/env python3
"""
Render docs/images/autopsy-demo.gif — README hero, maximally legible type.

1100×700 canvas: GitHub README images render ~830px wide, so a narrower GIF
barely downscales and chunky monospace stays readable. Content is short.
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

W, H = 1100, 700
HEADER_H = 104
PAD_X = 36
PAD_Y = 12
FOOTER_H = 40

# Fonts sized for the narrow canvas (see module docstring).
FONT_TITLE = 52
FONT_SUB = 24
FONT_CMD = 34
FONT_STEP = 34
FONT_BODY = 36
FONT_FOOT = 20
LINE_EXTRA = 10  # padding below each line (increases line spacing)


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
        try:
            return ImageFont.truetype(path, size=size)
        except (OSError, ValueError):
            continue
    return ImageFont.load_default()


def _wrap(raw: str, width: int) -> list[str]:
    raw = raw.rstrip("\n")
    if len(raw) <= width:
        return [raw]
    return textwrap.wrap(raw, width=width, break_long_words=True, replace_whitespace=False)


def _hr_chars_for_body() -> str:
    """Horizontal rule that fits content width for FONT_BODY."""
    char_w = max(10, int(FONT_BODY * 0.52))
    n = max(24, (W - 2 * PAD_X) // char_w)
    return "─" * n


def _run_deterministic(max_lines: int, wrap_w: int) -> list[str]:
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
        for part in _wrap(raw, wrap_w):
            lines.append(part)
            if len(lines) >= max_lines:
                return lines
    return lines


def _run_llm_live(max_lines: int, wrap_w: int, timeout: int) -> list[str] | None:
    if not (os.getenv("OPENROUTER_API_KEY") or "").strip():
        return None
    env = {**os.environ, "PYTHONWARNINGS": "ignore", "NO_COLOR": "1"}
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.cli",
            "analyze",
            str(TRACE),
            "-q",
            "-f",
            "text",
        ],
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
        for part in _wrap(raw, wrap_w):
            lines.append(part)
    return _truncate_middle(lines, max_lines)


def _truncate_middle(lines: list[str], max_lines: int) -> list[str]:
    if len(lines) <= max_lines:
        return lines
    head = max_lines // 2
    tail = max_lines - head - 3
    return lines[:head] + ["", "  …", ""] + lines[-tail:]


def _load_sample_llm(wrap_w: int) -> list[str]:
    lines: list[str] = []
    for ln in SAMPLE_LLM.read_text().splitlines():
        if not ln.strip():
            lines.append("")
        else:
            lines.extend(_wrap(ln, wrap_w))
    return lines


def _style_for_line(line: str) -> str:
    s = line.strip()
    if line.startswith("$"):
        return "cmd"
    if s.startswith("▸"):
        return "step"
    if s and all(c in "─═ " for c in s) and len(s) > 12:
        return "rule"
    if not s:
        return "blank"
    return "body"


def _line_height(font: ImageFont.ImageFont) -> int:
    try:
        bbox = font.getbbox("Mg")
        return bbox[3] - bbox[1] + LINE_EXTRA
    except Exception:
        return int(getattr(font, "size", FONT_BODY) * 1.45) + LINE_EXTRA


def _draw_header(draw: ImageDraw.ImageDraw, fonts: dict[str, ImageFont.ImageFont]) -> None:
    draw.rectangle((0, 0, W, HEADER_H), fill=(22, 27, 34))
    draw.text(
        (PAD_X, 18),
        "AGENT AUTOPSY",
        font=fonts["title"],
        fill=(255, 255, 255),
        stroke_width=2,
        stroke_fill=(10, 12, 16),
    )
    draw.text(
        (PAD_X, 98),
        "Demo: loop_failure.json",
        font=fonts["subtitle"],
        fill=(160, 170, 180),
        stroke_width=1,
        stroke_fill=(10, 12, 16),
    )


def _text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    *,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
    stroke: bool = True,
) -> None:
    if stroke:
        draw.text(
            xy,
            text,
            font=font,
            fill=fill,
            stroke_width=1,
            stroke_fill=(13, 17, 23),
        )
    else:
        draw.text(xy, text, font=font, fill=fill)


def _draw_frame(
    lines: list[str],
    *,
    fonts: dict[str, ImageFont.ImageFont],
    footer: str,
) -> Image.Image:
    bg = (13, 17, 23)
    img = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)
    _draw_header(draw, fonts)

    body_font = fonts["body"]
    lh = _line_height(body_font)
    y = HEADER_H + PAD_Y + 8
    x0 = PAD_X
    y_max = H - FOOTER_H - lh - 4

    for line in lines:
        if y > y_max:
            _text(draw, (x0, y), "…", font=body_font, fill=(139, 148, 158))
            break
        st = _style_for_line(line)

        if st == "cmd":
            _text(draw, (x0, y), line, font=fonts["cmd"], fill=(126, 231, 135))
        elif st == "step":
            _text(draw, (x0, y), line, font=fonts["step"], fill=(255, 180, 96))
        elif st == "rule":
            _text(draw, (x0, y), line, font=fonts["rule"], fill=(72, 82, 94), stroke=False)
        elif st == "blank":
            y += max(12, lh // 3)
            continue
        else:
            color = (230, 236, 243)
            if line.lstrip().startswith(("-", "•", "*")):
                color = (195, 204, 214)
            _text(draw, (x0, y), line, font=body_font, fill=color)
        y += lh

    draw.rectangle((0, H - FOOTER_H, W, H), fill=(17, 21, 28))
    fh = fonts["footer"]
    try:
        fb = fh.getbbox(footer)
        fy = H - FOOTER_H + (FOOTER_H - (fb[3] - fb[1])) // 2
    except Exception:
        fy = H - FOOTER_H + 16
    _text(draw, (PAD_X, fy), footer, font=fh, fill=(130, 138, 148), stroke=False)
    return img


def _build_script(cmd_lines: list[str], det: list[str], llm_lines: list[str]) -> list[str]:
    hr = _hr_chars_for_body()
    out: list[str] = []
    for ln in cmd_lines:
        out.append(ln)
    out.append("")
    out.append("▸ Step 1 — Deterministic (built-in patterns)")
    out.append(hr)
    for ln in det:
        out.append(("  " + ln) if ln else "")
    out.append("")
    out.append("▸ Step 2 — LLM synthesis (OpenRouter + tools)")
    out.append(hr)
    for ln in llm_lines:
        out.append(("  " + ln) if ln else "")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Render README demo GIF.")
    parser.add_argument("--force-sample-llm", action="store_true")
    parser.add_argument("--no-live-llm", action="store_true")
    parser.add_argument("--llm-timeout", type=int, default=150)
    args = parser.parse_args()
    _load_dotenv()

    wrap_w = 32  # short lines keep each char chunky on the narrow canvas
    det = _run_deterministic(3, wrap_w)

    try_live = not args.force_sample_llm and not args.no_live_llm
    used_live = False
    if args.force_sample_llm:
        llm_lines = _load_sample_llm(wrap_w)
    elif try_live:
        live = _run_llm_live(4, wrap_w, timeout=args.llm_timeout)
        if live:
            llm_lines = live
            used_live = True
        else:
            llm_lines = _load_sample_llm(wrap_w)
    else:
        llm_lines = _load_sample_llm(wrap_w)

    cmd_lines = [
        "$ autopsy analyze \\",
        "    examples/traces/loop_failure.json -q -f text",
    ]
    script_lines = _build_script(cmd_lines, det, llm_lines)

    max_lines = 12
    if len(script_lines) > max_lines:
        script_lines = script_lines[: max_lines - 1] + ["  …"]

    if used_live:
        footer = "Live OpenRouter + LangGraph  ·  agent-autopsy"
    else:
        footer = "Sample LLM lines when API offline  ·  agent-autopsy"

    rule_font = _mono_font(max(28, FONT_BODY - 12))
    fonts = {
        "title": _mono_font(FONT_TITLE),
        "subtitle": _mono_font(FONT_SUB),
        "cmd": _mono_font(FONT_CMD),
        "step": _mono_font(FONT_STEP),
        "body": _mono_font(FONT_BODY),
        "footer": _mono_font(FONT_FOOT),
        "rule": rule_font,
    }

    frames: list[Image.Image] = []
    for n in range(2, len(script_lines) + 1):
        frames.append(_draw_frame(script_lines[:n], fonts=fonts, footer=footer))

    if not frames:
        print("No frames generated", file=sys.stderr)
        return 2

    final = frames[-1]
    for _ in range(36):
        frames.append(final)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        OUT,
        save_all=True,
        append_images=frames[1:],
        duration=105,
        loop=0,
        optimize=True,
    )
    mode = "live LLM" if used_live else "deterministic + sample LLM"
    print(f"Wrote {OUT} ({len(frames)} frames @ {W}x{H}, {mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
