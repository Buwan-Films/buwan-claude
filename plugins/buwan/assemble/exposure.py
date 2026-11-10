"""Exposure: measure every camera clip and set the exposure fix the grade applies before the Buwan look.

Keyframes only (fast): average luma (YAVG), the 10th and 90th luma percentiles (YLOW / YHIGH), measured in 8-bit
(10-bit cameras are converted first, or every number is 4x too high).
The band is the studio look's own average-brightness target (kit/grade/targets.json, "bright", e.g. 55-150 for Warm).
Inside it: no fix. Outside it: Lumetri Basic Correction > Exposure nudges the clip just inside the band
(MARGIN from the edge, not to one fixed grey, so a bright garden stays bright and a night stays a night),
capped at +/-MAX_EV, never so far up that the 90th percentile clips (HIGHLIGHT_CAP).
Low-key by design (dark average AND nothing bright in the frame, e.g. rings on black) is left alone and listed.
White balance (whitebalance.py) is measured in the same pass and stored next to the exposure fix ("wb": RGB gains):
a gentle correction of colour casts that keeps natural warmth; aerials and clips without neutral areas are left alone.
The look LUT goes on after the fix. Writes edit/assemble/exposure.json; the Premiere manifest carries exposure_ev.
"""
from __future__ import annotations

import concurrent.futures as cf
import math
import re

from common import Clip, log, run
import whitebalance

BAND = (55.0, 150.0)     # fallback; the look's targets.json "bright" band wins
MARGIN = 10.0            # an out-of-band clip lands this far inside the band
LOW_KEY_HIGH = 60.0      # dark average with a 90th percentile under this = low-key by design, not under-exposed
MAX_EV = 1.5
HIGHLIGHT_CAP = 225.0
GAIN = 1.0               # stops per log2 of the luma ratio; Rec.709-ish footage under Lumetri. Recalibrate with grade-check.
WB_KEYS = ("temp", "tint", "wb_spread", "wb_frames", "wb_neutral")
NO_FIX = {"09 Music", "10 SFX & Ambience", "11 Graphics", "12 Grade & Adjust"}


def measure(clip: Clip) -> dict:
    r = run(["ffmpeg", "-v", "info", "-nostats", "-hide_banner", "-skip_frame", "nokey", "-i", clip.path, "-an",
             "-vf", "scale=320:-2,format=yuv420p,signalstats,metadata=print:file=-", "-f", "null", "-"], check=False, timeout=600)
    txt = (r.stdout or "") + (r.stderr or "")
    vals = {k: [float(x) for x in re.findall(rf"lavfi\.signalstats\.{k}=([\d.]+)", txt)] for k in ("YAVG", "YLOW", "YHIGH")}
    if not vals["YAVG"]:
        return {}
    return {k.lower(): round(sum(v) / len(v), 1) for k, v in vals.items() if v} | {"frames": len(vals["YAVG"])}


def load_band(look: str) -> tuple[float, float]:
    import json
    from pathlib import Path
    for cand in (Path.cwd() / "kit" / "grade" / "targets.json", Path.home() / ".buwan" / "kit" / "grade" / "targets.json",
                 Path(__file__).resolve().parent.parent / "kit" / "grade" / "targets.json"):
        try:
            b = json.loads(cand.read_text())[look]["bright"]
            return float(b[0]), float(b[1])
        except Exception:
            continue
    return BAND


def decide(m: dict, band: tuple[float, float] = BAND) -> dict:
    if not m:
        return {"ev": 0.0, "reason": "no picture data"}
    y = m["yavg"]
    if band[0] <= y <= band[1]:
        return {"ev": 0.0, "reason": f"average {y:.0f} inside the house band"}
    if y < band[0] and m.get("yhigh", 255) < LOW_KEY_HIGH:
        return {"ev": 0.0, "low_key": True, "reason": f"low-key by design (average {y:.0f}, nothing brighter than {m['yhigh']:.0f}): left alone, check by eye"}
    target = band[0] + MARGIN if y < band[0] else band[1] - MARGIN
    ev = GAIN * math.log2(target / max(y, 1.0))
    ev = max(-MAX_EV, min(MAX_EV, ev))
    why = f"average {y:.0f} {'under' if y < band[0] else 'over'} the house band {band[0]:.0f}-{band[1]:.0f}"
    if ev > 0 and m.get("yhigh"):
        cap = math.log2(HIGHLIGHT_CAP / max(m["yhigh"], 1.0))
        if cap < ev:
            ev = max(0.0, cap)
            why += f", held back to keep highlights (90th pct {m['yhigh']:.0f})"
    return {"ev": round(ev, 2), "reason": why}


def exposure(clips: list[Clip], categories: dict, rejected: set, workers: int = 6, look: str = "warm", previous: dict | None = None) -> dict:
    band = load_band(look)
    todo = [c for c in clips if c.kind == "video" and c.path not in rejected and categories.get(c.path) not in NO_FIX]
    prev = {p: v for p, v in (previous or {}).items() if v.get("yavg") is not None and v.get("frames")}
    res = {}
    for c in todo:   # measured before: decide again, don't re-read the footage
        if c.path in prev:
            m = {k: prev[c.path][k] for k in ("yavg", "ylow", "yhigh", "frames") if k in prev[c.path]}
            res[c.path] = {"name": c.name, "camera": c.camera, **m, **decide(m, band)}
            w = {k: prev[c.path][k] for k in WB_KEYS if k in prev[c.path]}
            if "wb_frames" in w:
                res[c.path].update(w | whitebalance.decide(w, c.camera))
    todo = [c for c in todo if c.path not in res]
    wb_todo = [c for c in clips if c.path in res and "wb_frames" not in res[c.path]]
    log(f"exposure: {look} band {band[0]:.0f}-{band[1]:.0f}; measuring {len(todo)} camera clips (keyframes), {len(res)} reused")
    def both(c):
        return measure(c), whitebalance.measure(c.path)

    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(both, c): c for c in todo}
        futs.update({ex.submit(lambda c=c: (None, whitebalance.measure(c.path))): c for c in wb_todo})
        if wb_todo:
            log(f"white balance: measuring {len(wb_todo)} clips measured for exposure before")
        for i, f in enumerate(cf.as_completed(futs), 1):
            c = futs[f]
            try:
                m, w = f.result()
            except Exception as e:
                m, w = {}, {}
                log(f"exposure: {c.name}: {e}")
            if m is not None:
                res[c.path] = {"name": c.name, "camera": c.camera, **m, **decide(m, band)}
            res[c.path].update({"wb_frames": 0} | (w or {}) | whitebalance.decide(w or {}, c.camera))
            if i % 100 == 0 or i == len(futs):
                log(f"exposure + white balance {i}/{len(futs)}")
    fixed = [v for v in res.values() if v["ev"]]
    up = sum(1 for v in fixed if v["ev"] > 0)
    lk = sum(1 for v in res.values() if v.get("low_key"))
    wbf = [v for v in res.values() if v.get("wb")]
    log(f"white balance: {len(wbf)} of {len(res)} clips get a fix "
        f"({sum(1 for v in wbf if v['wb_shift'][0] > 0)} too warm, {sum(1 for v in wbf if v['wb_shift'][0] < 0)} too blue, "
        f"{sum(1 for v in wbf if v['wb_shift'][1])} tint), the rest balanced or left alone")
    log(f"exposure: {len(fixed)} of {len(res)} clips get a fix ({up} brighter, {len(fixed) - up} darker), {lk} low-key left alone, the rest are inside the house band")
    return res
