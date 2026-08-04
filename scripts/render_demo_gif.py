#!/usr/bin/env python3
"""
Render docs/images/autopsy-demo.gif — a 20-second README/product demo.

1100×700 canvas: GitHub README images render ~830px wide, so a narrower GIF
barely downscales and chunky monospace stays readable. Content is short.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "images" / "autopsy-demo.gif"

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


def _hr_chars_for_body() -> str:
    """Horizontal rule that fits content width for FONT_BODY."""
    char_w = max(10, int(FONT_BODY * 0.52))
    n = max(24, (W - 2 * PAD_X) // char_w)
    return "─" * n


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


def main() -> int:
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

    # Five purposeful beats make the product legible in a short social/README
    # demo. Claims come directly from examples/traces/loop_failure.json.
    scenes = [
        [
            "▸ A failed agent run. One command to explain it.",
            "",
            "$ autopsy analyze loop_failure.json --no-llm",
        ],
        [
            "▸ Reading the trace locally…",
            "",
            "  ✓ 11 events normalized",
            "  ✓ Tool calls and errors mapped",
            "  ✓ Failure patterns checked",
        ],
        [
            "▸ ROOT CAUSE FOUND",
            _hr_chars_for_body(),
            "  Retry storm on web_search",
            "  7 identical calls · 7 timeouts",
            "  Ended with MaxRetriesError",
        ],
        [
            "▸ EVIDENCE",
            _hr_chars_for_body(),
            "  web_search repeated every 2s",
            "  Same input. Same timeout. No backoff.",
            "  Trace status: FAILED",
        ],
        [
            "▸ RECOMMENDED FIX",
            _hr_chars_for_body(),
            "  1. Cap retries at 3",
            "  2. Add exponential backoff",
            "  3. Stop retrying timeout failures",
            "",
            "  Debug agent traces locally.",
        ],
    ]
    footers = [
        "Agent Autopsy  ·  local-first agent debugging",
        "No upload  ·  No API key  ·  Deterministic",
        "Pattern detection with trace-backed evidence",
        "Every claim points back to the trace",
        "github.com/haseebraza715/agent-autopsy",
    ]
    frames = [
        _draw_frame(lines, fonts=fonts, footer=footer)
        for lines, footer in zip(scenes, footers)
    ]
    durations = [3000, 3500, 4500, 3500, 5500]  # 20 seconds total

    OUT.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        OUT,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    print(f"Wrote {OUT} ({len(frames)} scenes @ {W}x{H}, 20-second deterministic demo)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
