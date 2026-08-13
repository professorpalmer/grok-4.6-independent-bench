from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
JSON_PATH = ROOT / "deepswe-v1.1-grok-4.6.json"

W, H = 1400, 820
BG = (14, 18, 16)
INK = (236, 238, 232)
MUTED = (156, 164, 154)
RULE = (42, 50, 44)
LIME = (196, 232, 92)
BAR_BG = (32, 40, 34)
OTHER = (92, 108, 96)

# xAI grok-4.6 list, prompts <200k: https://docs.x.ai/developers/pricing
IN_USD = 2.00
CACHE_USD = 0.50
OUT_USD = 6.00
MODEL = "Grok 4.6 High"


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


def fmt_usd(value: float) -> str:
    return f"${value:.2f}"


def list_price_usd(fresh: float, cache: float, out: float) -> float:
    return fresh / 1e6 * IN_USD + cache / 1e6 * CACHE_USD + out / 1e6 * OUT_USD


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def our_cost(data: dict) -> dict:
    fresh: list[float] = []
    cache: list[float] = []
    out: list[float] = []
    for task in data["tasks"]:
        inp = task.get("n_input_tokens")
        cached = task.get("n_cache_tokens")
        output = task.get("n_output_tokens")
        if inp is None or output is None:
            continue
        cached = cached or 0
        cache.append(cached)
        fresh.append(max(0, inp - cached))
        out.append(output)
    usd = list_price_usd(mean(fresh), mean(cache), mean(out))
    return {
        "usd_per_task": round(usd, 2),
        "mean_fresh_tokens": round(mean(fresh), 1),
        "mean_cache_tokens": round(mean(cache), 1),
        "mean_output_tokens": round(mean(out), 1),
        "pricing": {
            "input_usd_per_mtok": IN_USD,
            "cached_input_usd_per_mtok": CACHE_USD,
            "output_usd_per_mtok": OUT_USD,
            "source": "https://docs.x.ai/developers/pricing",
        },
    }


def paint_header(d: ImageDraw.ImageDraw, kicker: str, title: str) -> None:
    d.text((64, 48), kicker, font=font(16), fill=LIME)
    d.text((64, 78), title, font=font(22, bold=True), fill=INK)


def paint_bars(
    d: ImageDraw.ImageDraw,
    rows: list[tuple[str, float, bool]],
    fmt,
    scale: float,
) -> None:
    bar_x, bar_w = 420, 780
    y0 = 430
    gap = 78
    lab = font(20, bold=True)
    val = font(20, bold=True)
    for i, (name, amount, mine) in enumerate(rows):
        y = y0 + i * gap
        color = LIME if mine else OTHER
        d.text((64, y + 8), name, font=lab, fill=INK if mine else MUTED)
        d.rounded_rectangle((bar_x, y + 10, bar_x + bar_w, y + 34), radius=4, fill=BAR_BG)
        fill_w = max(8, int(bar_w * amount / scale))
        d.rounded_rectangle((bar_x, y + 10, bar_x + fill_w, y + 34), radius=4, fill=color)
        d.text((bar_x + bar_w + 18, y + 8), fmt(amount), font=val, fill=INK if mine else MUTED)


def draw_pass(data: dict) -> None:
    score = data["score"]
    ours = float(score["pass_rate"])
    n = int(score["n_graded"])
    n_pass = int(score["n_pass"])
    universe = int(data["n_tasks"])
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    paint_header(d, "DEEPSWE v1.1", "Independent re-run")
    d.text((64, 168), fmt_pct(ours), font=font(112, bold=True), fill=INK)
    d.text((64, 292), MODEL, font=font(28, bold=True), fill=LIME)
    n_note = f"{n_pass}/{n} pass" + ("" if n == universe else f"  ·  {n} of {universe} graded")
    d.text((64, 338), n_note, font=font(16), fill=MUTED)
    d.line((64, 392, W - 64, 392), fill=RULE, width=1)
    paint_bars(
        d,
        [
            ("GPT-5.6 Sol Max", 0.73, False),
            ("Fable 5 Max", 0.70, False),
            (MODEL, ours, True),
            ("Grok 4.5 High", 0.54, False),
        ],
        fmt_pct,
        0.80,
    )
    d.text(
        (64, H - 58),
        f"{MODEL} is this independent Pier/Docker run. "
        "Other bars are Datacurve board scores (mini-swe-agent). "
        "xAI card lists Grok 4.6 High at 65.9%.",
        font=font(15),
        fill=MUTED,
    )
    out = ROOT / "deepswe-v1.1.png"
    img.save(out, "PNG")
    print("wrote", out)


def draw_cost(data: dict, cost: dict) -> None:
    ours = float(cost["usd_per_task"])
    baseline = 2.42
    ratio = ours / baseline
    out_ours = cost["mean_output_tokens"] / 1000
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    paint_header(d, "DEEPSWE v1.1", "Cost per task")
    d.text((64, 168), fmt_usd(ours), font=font(112, bold=True), fill=INK)
    d.text((64, 292), MODEL, font=font(28, bold=True), fill=LIME)
    d.text(
        (64, 338),
        f"{ratio:.1f}x Grok 4.5 High ({fmt_usd(baseline)})  ·  {out_ours:.0f}k vs 36k output tokens",
        font=font(16),
        fill=MUTED,
    )
    d.line((64, 392, W - 64, 392), fill=RULE, width=1)
    paint_bars(
        d,
        [
            ("Fable 5 Max", 21.63, False),
            ("GPT-5.6 Sol Max", 8.39, False),
            (MODEL, ours, True),
            ("Grok 4.5 High", 2.42, False),
        ],
        fmt_usd,
        24.0,
    )
    d.text(
        (64, H - 58),
        f"{MODEL} is xAI list on this run ($2 / $0.50 cache / $6 per MTok). "
        "Other bars are Datacurve billed USD. Output tokens rose vs Grok 4.5 High.",
        font=font(15),
        fill=MUTED,
    )
    out = ROOT / "deepswe-v1.1-cost.png"
    img.save(out, "PNG")
    print("wrote", out)


def main() -> None:
    data = json.loads(JSON_PATH.read_text())
    data["model"] = MODEL
    cost = our_cost(data)
    data["cost"] = cost
    JSON_PATH.write_text(json.dumps(data, indent=2) + "\n")
    draw_pass(data)
    draw_cost(data, cost)


if __name__ == "__main__":
    main()
