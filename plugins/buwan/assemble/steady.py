"""Steady: shaky footage on the Creative / Glider camera only.

For every clip from a camera whose folder name matches CREATIVE_CAMERAS and that the cull flagged
heavy-motion, measure the motion second by second and decide:

  best-cut   the longest steady stretch is at least MIN_STEADY_S long -> that range is the pick
             (Premiere: a subclip in <category>/Steady picks; Final Cut: a Favorite named "steady")
  warp       no steady stretch, but the shake is moderate -> Warp Stabilizer (Premiere: placed in the
             STABILIZE sequence with the effect applied; Final Cut: note "stabilize" — tick Stabilization)
  too-shaky  the whole clip is violent -> stays in 00 Flagged/Heavy motion

Other cameras are left alone: a shaky reaction shot is a reaction shot. Nothing is modified on disk.
"""
from __future__ import annotations

import concurrent.futures as cf
import re

from common import Clip, log, run

CREATIVE_CAMERAS = re.compile(r"creative|glider|gimbal|ronin|steadi|cine", re.I)
SAMPLE_FPS = 4
STEADY_MAX = 25.0       # per-sample motion under this = steady (YAVG of frame difference at 480px)
WARP_MAX_MEAN = 55.0    # mean motion above this is beyond what Warp Stabilizer saves
MIN_STEADY_S = 2.5      # a usable b-roll cut
PAD = 0.15


def is_creative(clip: Clip) -> bool:
    return bool(CREATIVE_CAMERAS.search(clip.camera or "") or CREATIVE_CAMERAS.search(clip.rel or ""))


def motion_profile(clip: Clip) -> list[float]:
    r = run(["ffmpeg", "-v", "info", "-nostats", "-hide_banner", "-i", clip.path, "-an", "-vf",
             f"fps={SAMPLE_FPS},scale=480:-2,tblend=all_mode=difference,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-",
             "-f", "null", "-"], check=False)
    # metadata=print:file=- lands on stdout on some ffmpeg builds and stderr on others
    return [float(x) for x in re.findall(r"lavfi\.signalstats\.YAVG=([\d.]+)", (r.stdout or "") + (r.stderr or ""))]


def decide(clip: Clip, motion: list[float]) -> dict:
    n = len(motion)
    if not n:
        return {"name": clip.name, "path": clip.path, "camera": clip.camera, "decision": "warp", "reason": "no motion data"}
    mean = sum(motion) / n
    # longest run of steady samples
    best, cur_start, cur_len, best_start = 0, 0, 0, 0
    for i, v in enumerate(motion):
        if v < STEADY_MAX:
            if cur_len == 0:
                cur_start = i
            cur_len += 1
            if cur_len > best:
                best, best_start = cur_len, cur_start
        else:
            cur_len = 0
    steady_s = best / SAMPLE_FPS
    out = {"name": clip.name, "path": clip.path, "camera": clip.camera, "mean_motion": round(mean, 1), "steady_s": round(steady_s, 1)}
    if steady_s >= MIN_STEADY_S:
        a = max(0.0, best_start / SAMPLE_FPS + PAD)
        b = min(clip.duration, (best_start + best) / SAMPLE_FPS - PAD)
        out.update(decision="best-cut", range=[round(a, 3), round(b, 3)], reason=f"{steady_s:.1f}s steady stretch")
    elif mean <= WARP_MAX_MEAN:
        out.update(decision="warp", reason=f"no steady stretch (longest {steady_s:.1f}s), shake moderate (mean {mean:.0f})")
    else:
        out.update(decision="too-shaky", reason=f"mean motion {mean:.0f}, nothing to save")
    return out


def steady(clips: list[Clip], cull: list[dict], workers: int = 4) -> dict:
    flagged = {m["path"] for m in cull if "heavy-motion" in (m.get("warn") or []) and not m.get("reject")}
    todo = [c for c in clips if c.kind == "video" and is_creative(c) and c.path in flagged]
    skipped = sum(1 for c in clips if c.kind == "video" and not is_creative(c) and c.path in flagged)
    log(f"steady: {len(todo)} shaky Creative/Glider clips to judge ({skipped} shaky clips on other cameras left alone)")
    res = {}
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(motion_profile, c): c for c in todo}
        for i, f in enumerate(cf.as_completed(futs), 1):
            c = futs[f]
            try:
                res[c.path] = decide(c, f.result())
            except Exception as e:
                res[c.path] = {"name": c.name, "path": c.path, "camera": c.camera, "decision": "warp", "reason": f"measure error: {e}"}
            if i % 10 == 0 or i == len(futs):
                log(f"steady {i}/{len(futs)}")
    counts = {k: sum(1 for v in res.values() if v["decision"] == k) for k in ("best-cut", "warp", "too-shaky")}
    log(f"steady: {counts['best-cut']} best cuts, {counts['warp']} for Warp Stabilizer, {counts['too-shaky']} too shaky")
    return res
