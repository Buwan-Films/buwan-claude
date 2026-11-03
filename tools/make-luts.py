#!/usr/bin/env python3
"""Generate the Buwan starting looks as 33-point .cube LUTs (Rec.709 in -> Rec.709 out).

These are STARTING looks built from the written house grade ("muted filmic, warm/naturalistic
or cool/desaturated, B&W for intimate beats"). Apply them AFTER the camera's own Log->Rec.709
conversion, at 60-100% strength. When the studio has a reference grade it likes, export that
look from Resolve as a 33-point .cube and replace these files.

Usage: python3 tools/make-luts.py plugins/buwan/kit/luts
"""
import math, os, sys

N = 33
OUT = sys.argv[1] if len(sys.argv) > 1 else "."

def s_curve(x, k):
    return 0.5 + 0.5 * math.tanh(k * (x - 0.5)) / math.tanh(k * 0.5)

def hue_of(r, g, b):
    mx, mn = max(r, g, b), min(r, g, b)
    if mx - mn < 1e-6:
        return 0.0
    if mx == r:
        h = ((g - b) / (mx - mn)) % 6
    elif mx == g:
        h = (b - r) / (mx - mn) + 2
    else:
        h = (r - g) / (mx - mn) + 4
    return h * 60

LOOKS = {
    "Buwan_Warm": dict(k=1.5, floor=0.035, ceil=0.94, sat=0.84, hi_desat=0.25, skin=0.10,
                       shadows=(-0.010, 0.002, 0.010), mids=(0.010, 0.002, -0.012), highs=(0.026, 0.010, -0.030)),
    "Buwan_Cool": dict(k=1.45, floor=0.040, ceil=0.93, sat=0.76, hi_desat=0.30, skin=0.10,
                       shadows=(-0.008, 0.006, 0.014), mids=(-0.004, 0.002, 0.006), highs=(-0.014, 0.000, 0.020)),
    "Buwan_BW":   dict(k=1.9, floor=0.030, ceil=0.95, sat=0.0, hi_desat=0.0, skin=0.0, bw=(0.35, 0.55, 0.10),
                       shadows=(0.0, 0.0, 0.0), mids=(0.004, 0.0, -0.004), highs=(0.006, 0.002, -0.006)),
}

def apply(look, r, g, b):
    L = look
    if "bw" in L:
        wr, wg, wb = L["bw"]
        y = wr * r + wg * g + wb * b
        r = g = b = y
    # tone curve on each channel through luma ratio (keeps hue)
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    yc = L["floor"] + (L["ceil"] - L["floor"]) * s_curve(y, L["k"])
    scale = yc / y if y > 1e-5 else 0
    r, g, b = (r * scale, g * scale, b * scale) if y > 1e-5 else (yc, yc, yc)
    # saturation: muted overall, more muted in highlights, skin protected
    if "bw" not in L:
        y2 = 0.2126 * r + 0.7152 * g + 0.0722 * b
        sat = L["sat"] * (1 - L["hi_desat"] * max(0.0, y2 - 0.6) / 0.4)
        h = hue_of(r, g, b)
        if 10 <= h <= 50:
            sat = min(1.0, sat + L["skin"] * (1 - abs(h - 30) / 20))
        r, g, b = (y2 + (c - y2) * sat for c in (r, g, b))
    # split tone by luma zone
    y3 = 0.2126 * r + 0.7152 * g + 0.0722 * b
    ws = max(0.0, 1 - y3 / 0.35)
    wh = max(0.0, (y3 - 0.6) / 0.4)
    wm = max(0.0, 1 - ws - wh)
    out = []
    for i, c in enumerate((r, g, b)):
        c += ws * L["shadows"][i] + wm * L["mids"][i] + wh * L["highs"][i]
        out.append(min(1.0, max(0.0, c)))
    return out

os.makedirs(OUT, exist_ok=True)
for name, look in LOOKS.items():
    path = os.path.join(OUT, f"{name}.cube")
    with open(path, "w") as f:
        f.write(f'TITLE "{name.replace("_", " ")} (starting look)"\n# Buwan Films. Rec.709 in/out. Apply after camera Log->709 conversion.\n')
        f.write(f"LUT_3D_SIZE {N}\nDOMAIN_MIN 0.0 0.0 0.0\nDOMAIN_MAX 1.0 1.0 1.0\n")
        for bi in range(N):
            for gi in range(N):
                for ri in range(N):
                    r, g, b = apply(look, ri / (N - 1), gi / (N - 1), bi / (N - 1))
                    f.write(f"{r:.6f} {g:.6f} {b:.6f}\n")
    print("wrote", path)
