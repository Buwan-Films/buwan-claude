"""Edit map: a PNG overview of a built timeline — music energy, speech spine, b-roll by category, markers.
Lets the editor (and Claude) review the shape of the cut before importing it."""
from __future__ import annotations

from pathlib import Path

CAT_COLORS = {
    "01 Speech": (255, 170, 0), "02 Prep & Details": (210, 180, 140), "03 Portraits": (240, 220, 80), "04 Ceremony": (150, 110, 220),
    "05 Reactions & BTS": (240, 130, 170), "06 Establishing": (90, 170, 230), "07 Reception & Party": (220, 90, 200), "08 Drone": (80, 200, 190),
    "unsorted": (140, 140, 140),
}


def draw_map(plan: dict, music: dict, categories: dict, out_png: str, px_per_s: float = 6.0):
    from PIL import Image, ImageDraw, ImageFont
    total = plan["stats"]["total_s"]
    W = int(total * px_per_s) + 160
    H = 330
    im = Image.new("RGB", (W, H), (13, 12, 10))
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype(str(Path(__file__).parent.parent / "kit" / "fonts" / "Cinzel-Regular.ttf"), 12)
        small = ImageFont.truetype(str(Path(__file__).parent.parent / "kit" / "fonts" / "CormorantGaramond-Medium.ttf"), 13)
    except Exception:
        font = small = ImageFont.load_default()
    X0 = 120
    x = lambda t: X0 + t * px_per_s
    gold = (201, 162, 75)
    # time axis
    for s in range(0, int(total) + 1, 15):
        d.line([(x(s), 20), (x(s), H - 10)], fill=(40, 38, 32))
        d.text((x(s) + 2, 4), f"{s // 60}:{s % 60:02d}", fill=(140, 134, 120), font=small)
    rows = {"music": (40, 70), "speech": (110, 150), "broll": (185, 225), "marks": (255, 300)}
    for name, (y0, y1) in rows.items():
        d.text((8, y0 + 2), {"music": "MUSIC", "speech": "SPEECH", "broll": "B-ROLL", "marks": "MARKERS"}[name], fill=gold, font=font)
    # music energy
    intro_s = plan["stats"]["intro_s"]
    for key, t0 in (("intro", 0.0), ("main", intro_s)):
        tr = music.get(key)
        if not tr:
            continue
        e = tr["energy_10hz"]
        y0, y1 = rows["music"]
        pts = [(x(t0 + i * 0.1), y1 - v * (y1 - y0)) for i, v in enumerate(e)]
        if len(pts) > 1:
            d.line(pts, fill=(120, 200, 120), width=1)
        p0, p1 = tr["sections"]["peak"]
        d.rectangle([x(t0 + p0), y0, x(t0 + p1), y1], outline=(230, 120, 120))
        d.text((x(t0) + 3, y0 - 14), f"track {1 if key == 'intro' else 2} · {tr['tempo_bpm']:.0f} bpm", fill=(120, 200, 120), font=small)
        for b in tr["bars"]:
            d.line([(x(t0 + b), y1 - 3), (x(t0 + b), y1)], fill=(120, 200, 120))
    # speech spine
    y0, y1 = rows["speech"]
    for s in plan["spine"]:
        if s.get("gap"):
            continue
        d.rectangle([x(s["at"]), y0, x(s["at"] + s["dur"]), y1], fill=(255, 170, 0), outline=(13, 12, 10))
        label = s.get("name", "")[:18]
        d.text((x(s["at"]) + 2, y0 + 2), label, fill=(13, 12, 10), font=small)
        if any("HOLD" in m["name"] for m in s.get("markers", [])):
            d.text((x(s["at"]) + 2, y1 - 15), "HOLD", fill=(13, 12, 10), font=font)
    # b-roll
    y0, y1 = rows["broll"]
    for c in plan["connected"]:
        if c.get("lane", 0) <= 0:
            continue
        dur = (c["out"] - c["in"]) * ((plan["clips"][c["clip"]]["fps_num"] / plan["clips"][c["clip"]]["fps_den"]) / (24000 / 1001) if c.get("slowmo") else 1)
        col = CAT_COLORS.get(categories.get(c["clip"], "unsorted"), (140, 140, 140))
        d.rectangle([x(c["at"]), y0, x(c["at"] + dur), y1], fill=col, outline=(13, 12, 10))
    # markers
    y0, y1 = rows["marks"]
    for s in plan["spine"]:
        for m in s.get("markers", []):
            t = s["at"] + m["t"]
            name = m["name"]
            if name.startswith("PART"):
                d.line([(x(t), 20), (x(t), H - 10)], fill=gold)
                d.text((x(t) + 3, y0), name.replace("PART: ", ""), fill=gold, font=font)
            elif name.startswith("GRAPHIC") or name.startswith("MUSIC"):
                d.polygon([(x(t), y0 + 18), (x(t) - 5, y0 + 28), (x(t) + 5, y0 + 28)], fill=(230, 206, 140))
                d.text((x(t) + 6, y0 + 20), name.split(" (")[0][:34], fill=(230, 206, 140), font=small)
    # legend
    lx = X0
    for k, col in CAT_COLORS.items():
        if k in ("01 Speech", "unsorted"):
            continue
        d.rectangle([lx, H - 22, lx + 10, H - 12], fill=col)
        d.text((lx + 14, H - 24), k[3:], fill=(200, 194, 180), font=small)
        lx += 14 + 7 * len(k)
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    im.save(out_png)
    return out_png
