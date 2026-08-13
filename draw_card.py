from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
JSON_PATH = ROOT / "deepswe-v1.1-grok-4.6.json"
OUT = ROOT / "deepswe-v1.1.png"

W, H = 1400, 820
BG = (14, 18, 16)
INK = (236, 238, 232)
MUTED = (156, 164, 154)
RULE = (42, 50, 44)
LIME = (196, 232, 92)
BAR_BG = (32, 40, 34)
OTHER = (92, 108, 96)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    names = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    for name in names:
        path = Path(name)
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def fmt_pct(rate: float) -> str:
    pct = rate * 100
    if abs(pct - round(pct)) < 0.05:
        return f"{int(round(pct))}%"
    return f"{pct:.1f}%"


def main() -> None:
    data = json.loads(JSON_PATH.read_text())
    score = data["score"]
    ours = float(score["pass_rate"])
    n = int(score["n_graded"])
    n_pass = int(score["n_pass"])
    universe = int(data["n_tasks"])
    rows = [
        ("GPT-5.6 Sol Max", 0.73, False),
        ("Fable 5 Max", 0.70, False),
        ("Grok 4.6", ours, True),
        ("Grok 4.5 High", 0.54, False),
    ]

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    title = font(22, bold=True)
    kicker = font(16)
    hero = font(112, bold=True)
    hero_sub = font(28, bold=True)
    label = font(20, bold=True)
    pctf = font(20, bold=True)
    foot = font(15)

    d.text((64, 48), "DEEPSWE v1.1", font=kicker, fill=LIME)
    d.text((64, 78), "Independent re-run", font=title, fill=INK)
    d.text((64, 168), fmt_pct(ours), font=hero, fill=INK)
    d.text((64, 292), "Grok 4.6", font=hero_sub, fill=LIME)
    n_note = f"{n_pass}/{n} pass" + ("" if n == universe else f"  ·  {n} of {universe} graded")
    d.text((64, 338), n_note, font=kicker, fill=MUTED)

    d.line((64, 392, W - 64, 392), fill=RULE, width=1)

    bar_x, bar_w = 420, 780
    y0 = 430
    gap = 78
    for i, (name, rate, mine) in enumerate(rows):
        y = y0 + i * gap
        color = LIME if mine else OTHER
        d.text((64, y + 8), name, font=label, fill=INK if mine else MUTED)
        d.rounded_rectangle((bar_x, y + 10, bar_x + bar_w, y + 34), radius=4, fill=BAR_BG)
        fill_w = max(8, int(bar_w * rate / 0.80))
        d.rounded_rectangle((bar_x, y + 10, bar_x + fill_w, y + 34), radius=4, fill=color)
        d.text((bar_x + bar_w + 18, y + 8), fmt_pct(rate), font=pctf, fill=INK if mine else MUTED)

    caption = (
        "Grok 4.6 is this independent Pier/Docker run. "
        "Other bars are Datacurve board scores (mini-swe-agent). "
        "xAI card lists Grok 4.6 at 65.9%."
    )
    d.text((64, H - 58), caption, font=foot, fill=MUTED)
    img.save(OUT, "PNG")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
