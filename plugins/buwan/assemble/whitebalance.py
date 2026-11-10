"""White balance: measure the colour cast of every camera clip and set a gentle per-channel fix, before the look.

How it reads a clip: the keyframes, scaled down, and only the near-neutral pixels (mid brightness, the least
saturated quarter: white dresses, barong, walls, grey suits, the sky's overcast). Their average R, G, B is the cast.
Two axes, in stops:
  temp = log2(R/B)              + = warm/amber, - = cool/blue
  tint = log2(G / sqrt(R*B))    + = green (LED, fluorescent, foliage spill), - = magenta
Studio policy (Philippine weddings, the Buwan Warm look goes on later):
  - natural warmth is kept: up to WARM_KEEP stops warm is left alone (golden hour, tungsten receptions stay warm);
    only the warmth beyond it is pulled back, and only partly (WARM_PULL)
  - a blue cast (camera on daylight in the shade, wrong preset) is corrected most of the way (COOL_PULL)
  - green/magenta tint is corrected most of the way (TINT_PULL) - it is never a look
  - every fix is capped at MAX_STOPS per axis; a clip with too few neutral pixels (a colourful stage, LED walls,
    a close-up of flowers) or a cast that swings between keyframes (mixed light) is left alone and listed
The fix is a per-channel gain that keeps the brightness (Rec.709 luma weights), applied in the render
together with the exposure fix. Stored per clip in exposure.json as "wb": [r, g, b] gains.
"""
from __future__ import annotations

import math
import subprocess

import numpy as np

W, H = 96, 54
MIN_NEUTRAL = 0.10       # share of the frame that must be near-neutral to trust the reading
AERIAL = ("drone", "dji", "aerial", "mavic")   # aerials: sky haze and foliage, no neutral reference -> left alone
WARM_KEEP = 0.30         # stops of warmth that are natural and kept
WARM_PULL = 0.6
COOL_KEEP = 0.05
COOL_PULL = 0.8
TINT_KEEP = 0.04
TINT_PULL = 0.9
MAX_STOPS = 0.5
MAX_SPREAD = 0.35        # keyframe-to-keyframe swing (stops) above which the light is mixed: no fix
MIN_FIX = 0.04           # smaller fixes are not worth a render change


def _frames(path: str, max_frames: int = 24) -> np.ndarray | None:
    cmd = ["ffmpeg", "-v", "error", "-nostats", "-skip_frame", "nokey", "-i", path, "-an",
           "-vf", f"scale={W}:{H}:in_color_matrix=bt709:flags=area,format=rgb24", "-fps_mode", "passthrough",
           "-f", "rawvideo", "-"]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=900)
    except subprocess.TimeoutExpired:
        return None
    n = len(r.stdout) // (W * H * 3)
    if not n:
        return None
    a = np.frombuffer(r.stdout[: n * W * H * 3], np.uint8).reshape(n, H, W, 3).astype(np.float32)
    if n > max_frames:
        a = a[np.linspace(0, n - 1, max_frames).round().astype(int)]
    return a


def _cast(frame: np.ndarray) -> tuple[float, float, float] | None:
    """The cast of the frame's neutral surfaces. Mean shift in log-chroma (temp, tint), starting from neutral:
    it walks to the nearest dense cluster of greyish pixels (a warm, blue or green cast moves that whole cluster),
    not to the average colour of the scene, and not to skin (far warmer) when there is anything neutral in frame."""
    px = frame.reshape(-1, 3).astype(np.float64) + 1.0
    r, g, b = px[:, 0], px[:, 1], px[:, 2]
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    mx, mn = px.max(1), px.min(1)
    ok = (y > 40) & (y < 220) & (mx < 251) & ((mx - mn) / mx < 0.55)
    if ok.sum() < MIN_NEUTRAL * len(px) * 1.5:
        return None
    t = np.log2(r[ok] / b[ok]); tn = np.log2(g[ok] / np.sqrt(r[ok] * b[ok]))
    c = np.array([0.0, 0.0])
    for sig in (0.35, 0.25, 0.18, 0.12, 0.12, 0.12):
        w = np.exp(-((t - c[0]) ** 2 + (tn - c[1]) ** 2) / (2 * sig * sig))
        if w.sum() < 1e-6:
            return None
        c = np.array([(w * t).sum() / w.sum(), (w * tn).sum() / w.sum()])
    share = float((((t - c[0]) ** 2 + (tn - c[1]) ** 2) < 0.12 ** 2).sum() / len(px))
    if share < MIN_NEUTRAL:
        return None
    return float(c[0]), float(c[1]), share


def measure(path: str) -> dict:
    fr = _frames(path)
    if fr is None:
        return {}
    casts = [c for c in (_cast(f) for f in fr) if c]
    if len(casts) < max(1, len(fr) // 3):
        return {"wb_frames": len(fr), "wb_neutral": round(len(casts) / max(len(fr), 1), 2)}
    t = np.array([c[0] for c in casts]); g = np.array([c[1] for c in casts])
    return {"temp": round(float(np.median(t)), 3), "tint": round(float(np.median(g)), 3),
            "wb_spread": round(float(max(np.quantile(t, .9) - np.quantile(t, .1), np.quantile(g, .9) - np.quantile(g, .1))), 3),
            "wb_frames": len(fr), "wb_neutral": round(float(np.median([c[2] for c in casts])), 3)}


def _gains(dt: float, dg: float) -> list[float]:
    """Correction in stops (dt: make it this much cooler(+)/warmer(-), dg: this much less green) -> RGB gains, luma kept."""
    r = 2 ** (-dt / 2 + dg / 3)
    b = 2 ** (dt / 2 + dg / 3)
    gg = 2 ** (-2 * dg / 3)
    k = 0.2126 * r + 0.7152 * gg + 0.0722 * b
    return [round(r / k, 4), round(gg / k, 4), round(b / k, 4)]


def decide(m: dict, camera: str = "") -> dict:
    if any(k in (camera or "").lower() for k in AERIAL):
        return {"wb": None, "wb_reason": "aerial (sky and foliage, nothing neutral to read): left alone"}
    if "temp" not in m:
        return {"wb": None, "wb_reason": "too few neutral areas to read the white balance: left alone" if m else "no picture data"}
    if m["wb_spread"] > MAX_SPREAD:
        return {"wb": None, "wb_reason": f"the light changes through the clip (swing {m['wb_spread']:.2f} stops): left alone, check by eye"}
    t, g = m["temp"], m["tint"]
    if t > WARM_KEEP:
        dt = min(MAX_STOPS, (t - WARM_KEEP) * WARM_PULL)
    elif t < -COOL_KEEP:
        dt = max(-MAX_STOPS, (t + COOL_KEEP) * COOL_PULL)
    else:
        dt = 0.0
    dg = 0.0 if abs(g) <= TINT_KEEP else max(-MAX_STOPS, min(MAX_STOPS, (g - math.copysign(TINT_KEEP, g)) * TINT_PULL))
    if abs(dt) < MIN_FIX and abs(dg) < MIN_FIX:
        return {"wb": None, "wb_reason": f"balanced (temp {t:+.2f}, tint {g:+.2f})"}
    bits = []
    if abs(dt) >= MIN_FIX:
        bits.append(f"{'too warm' if dt > 0 else 'too blue'} {t:+.2f} -> {t - dt:+.2f}")
    if abs(dg) >= MIN_FIX:
        bits.append(f"{'green' if dg > 0 else 'magenta'} tint {g:+.2f} -> {g - dg:+.2f}")
    return {"wb": _gains(dt, dg), "wb_shift": [round(dt, 3), round(dg, 3)], "wb_reason": "; ".join(bits)}
