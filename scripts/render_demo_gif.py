#!/usr/bin/env python3
"""
Render docs/images/autopsy-demo.gif from a real `autopsy analyze` run.

Layout: 1920×1080, large monospace (no downscale — text stays readable on GitHub).
Structure: header bar → command → Step 1 (deterministic) → Step 2 (LLM excerpt).

Deterministic block always from CLI (--no-llm). LLM block from live API when
OPENROUTER_API_KEY works, else scripts/demo_gif_llm_sample.txt.
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

# Final frame — full HD so README hero stays legible
W, H = 1920, 1080
HEADER_H = 108
PAD_X = 56
PAD_Y = 28
FOOTER_H = 52


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
    raw = raw.rstrip("\n")
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
    wrap_w = 76
    for raw in body.splitlines():
        for part in _wrap(raw, wrap_w):
            lines.append(part)
            if len(lines) >= max_lines:
                return lines
    return lines


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
    wrap_w = 76
    for raw in body.splitlines():
        for part in _wrap(raw, wrap_w):
            lines.append(part)
    return _truncate_middle(lines, max_lines)


def _truncate_middle(lines: list[str], max_lines: int) -> list[str]:
    if len(lines) <= max_lines:
        return lines
    head = max_lines // 2
    tail = max_lines - head - 3
    return lines[:head] + ["", "  … truncated …", ""] + lines[-tail:]


def _load_sample_llm() -> list[str]:
    lines: list[str] = []
    for ln in SAMPLE_LLM.read_text().splitlines():
        if not ln.strip():
            lines.append("")
        else:
            lines.extend(_wrap(ln, 76))
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


def _draw_header(draw: ImageDraw.ImageDraw, fonts: dict[str, ImageFont.ImageFont]) -> None:
    draw.rectangle((0, 0, W, HEADER_H), fill=(22, 27, 34))
    draw.text((PAD_X, 22), "AGENT AUTOPSY", font=fonts["title"], fill=(255, 255, 255))
    draw.text(
        (PAD_X, 68),
        "Demo trace: examples/traces/loop_failure.json",
        font=fonts["subtitle"],
        fill=(139, 148, 158),
    )


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
    try:
        bbox = body_font.getbbox("Ay")
        lh = bbox[3] - bbox[1] + 12
    except Exception:
        lh = int(getattr(body_font, "size", 32) * 1.4) + 12

    y = HEADER_H + PAD_Y
    x0 = PAD_X
    y_max = H - FOOTER_H - lh

    for line in lines:
        if y > y_max:
            draw.text((x0, y), "…", font=body_font, fill=(139, 148, 158))
            break
        st = _style_for_line(line)

        if st == "cmd":
            draw.text((x0, y), line, font=fonts["cmd"], fill=(126, 231, 135))
        elif st == "step":
            draw.text((x0, y), line, font=fonts["step"], fill=(255, 166, 87))
        elif st == "rule":
            draw.text((x0, y), line, font=body_font, fill=(88, 96, 106))
        elif st == "blank":
            y += lh // 2
            continue
        else:
            color = (220, 227, 235)
            if line.lstrip().startswith(("-", "•", "*")):
                color = (187, 196, 206)
            draw.text((x0, y), line, font=body_font, fill=color)
        y += lh

    # Footer strip
    draw.rectangle((0, H - FOOTER_H, W, H), fill=(17, 21, 28))
    draw.text((PAD_X, H - FOOTER_H + 14), footer, font=fonts["footer"], fill=(110, 118, 129))
    return img


def _hr() -> str:
    return "─" * 88


def _build_script(cmd_line: str, det: list[str], llm_lines: list[str]) -> list[str]:
    return [
        cmd_line,
        "",
        "▸ Step 1 — Deterministic scan (patterns + health score)",
        _hr(),
        *[("  " + ln) if ln else "" for ln in det],
        "",
        "▸ Step 2 — LLM synthesis (OpenRouter + LangGraph tools)",
        _hr(),
        *[("  " + ln) if ln else "" for ln in llm_lines],
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Render README demo GIF.")
    parser.add_argument("--force-sample-llm", action="store_true")
    parser.add_argument("--no-live-llm", action="store_true")
    parser.add_argument("--llm-timeout", type=int, default=150)
    args = parser.parse_args()
    _load_dotenv()

    det = _run_deterministic(9)
    try_live = not args.force_sample_llm and not args.no_live_llm
    used_live = False
    if args.force_sample_llm:
        llm_lines = _load_sample_llm()
    elif try_live:
        live = _run_llm_live(14, timeout=args.llm_timeout)
        if live:
            llm_lines = live
            used_live = True
        else:
            llm_lines = _load_sample_llm()
    else:
        llm_lines = _load_sample_llm()

    cmd_line = "$ autopsy analyze examples/traces/loop_failure.json -q -f text"
    script_lines = _build_script(cmd_line, det, llm_lines)

    # Hard cap so nothing clips on 1080p layout
    max_lines = 26
    if len(script_lines) > max_lines:
        script_lines = script_lines[: max_lines - 1] + ["  …"]

    if used_live:
        footer = "Live OpenRouter + LangGraph  ·  agent-autopsy"
    else:
        footer = "Representative LLM block when API unavailable  ·  agent-autopsy"

    fonts = {
        "title": _mono_font(44),
        "subtitle": _mono_font(26),
        "cmd": _mono_font(30),
        "step": _mono_font(30),
        "body": _mono_font(32),
        "footer": _mono_font(22),
    }

    frames: list[Image.Image] = []
    for n in range(2, len(script_lines) + 1):
        frames.append(_draw_frame(script_lines[:n], fonts=fonts, footer=footer))

    if not frames:
        print("No frames generated", file=sys.stderr)
        return 2

    final = frames[-1]
    for _ in range(32):
        frames.append(final)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        OUT,
        save_all=True,
        append_images=frames[1:],
        duration=95,
        loop=0,
        optimize=True,
    )
    mode = "live LLM" if used_live else "deterministic + sample LLM"
    print(f"Wrote {OUT} ({len(frames)} frames @ {W}x{H}, {mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
