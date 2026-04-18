#!/usr/bin/env python3
"""
Render docs/images/autopsy-demo.gif from a real `autopsy analyze` run (no LLM).

Uses Pillow only (no asciinema/agg). Dark terminal styling, line-by-line reveal.
"""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "images" / "autopsy-demo.gif"


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


def _run_demo() -> list[str]:
    env = {**os.environ, "PYTHONWARNINGS": "ignore", "NO_COLOR": "1"}
    cmd = [
        sys.executable,
        "-m",
        "src.cli",
        "analyze",
        str(REPO / "examples" / "traces" / "loop_failure.json"),
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
    lines = [
        "$ autopsy analyze examples/traces/loop_failure.json --no-llm -q -f text",
        "",
    ]
    for raw in body.splitlines():
        # Wrap very long lines for narrow terminal aesthetic
        if len(raw) <= 98:
            lines.append(raw)
        else:
            lines.extend(textwrap.wrap(raw, width=98, break_long_words=True, replace_whitespace=False))
    return lines[:52]


def _draw_frame(lines: list[str], w: int, h: int, font: ImageFont.ImageFont) -> Image.Image:
    bg = (13, 17, 23)  # github-dark-ish
    fg = (201, 209, 217)
    accent = (126, 231, 135)  # prompt green
    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)
    x0, y0 = 20, 20
    y = y0
    lh = font.getbbox("Ay")[3] - font.getbbox("Ay")[1] + 4
    for i, line in enumerate(lines):
        if y + lh > h - 16:
            break
        color = accent if i == 0 and line.startswith("$") else fg
        draw.text((x0, y), line, font=font, fill=color)
        y += lh
    draw.text((x0, h - 28), "agent-autopsy — deterministic autopsy", font=font, fill=(110, 118, 129))
    return img


def main() -> int:
    lines = _run_demo()
    if len(lines) < 3:
        print("Demo output too short:", lines, file=sys.stderr)
        return 2

    font = _mono_font(15)
    w, h = 920, 520
    frames: list[Image.Image] = []
    # Progressive reveal
    for n in range(2, len(lines) + 1, 1):
        frames.append(_draw_frame(lines[:n], w, h, font))
    # Hold on final frame
    final = frames[-1]
    for _ in range(18):
        frames.append(final)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    duration_ms = 95
    frames[0].save(
        OUT,
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0,
        optimize=True,
    )
    print(f"Wrote {OUT} ({len(frames)} frames)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
