"""Steady: shaky footage on the Creative / Glider camera only.

For every clip from a camera whose folder name matches CREATIVE_CAMERAS and that the cull flagged
heavy-motion, measure the motion second by second. The best cut is always selected first; only gimbal
shots are stabilized, and only when no steady cut exists:

  best-cut   the longest steady stretch is at least MIN_STEADY_S long -> that range is the pick, no
             stabilizing (Premiere: a subclip in <category>/Steady picks; Final Cut: a Favorite "steady")
  warp       no steady stretch, the clip is a GIMBAL shot and the shake is moderate -> Warp Stabilizer on
             the best (least-shaky) cut of the clip, not the whole clip (Premiere: that range placed in the
             STABILIZE sequence with the effect applied; Final Cut: keyword "stabilize" + the range in the note)
  handheld   no steady stretch and not a gimbal shot -> not stabilized; stays in 00 Flagged/Heavy motion
             with its best cut in the reason
  too-shaky  the whole clip is violent -> stays in 00 Flagged/Heavy motion

Gimbal shots: the camera/folder name says so (GIMBAL_CAMERAS), or the editor lists them in
edit/assemble/gimbal.txt (one pattern per line, matched against the clip's relative path: a card folder
like "1-Creative/5/", a clip name like "C0022", or "*" for every Creative clip), or --gimbal on the
command line. A "Creative" folder alone is not proof of a gimbal.
Other cameras are left alone: a shaky reaction shot is a reaction shot. Nothing is modified on disk.
"""
from __future__ import annotations

import concurrent.futures as cf
import fnmatch
import re

from common import Clip, log, run

CREATIVE_CAMERAS = re.compile(r"creative|glider|gimbal|ronin|steadi|cine", re.I)
GIMBAL_CAMERAS = re.compile(r"glider|gimbal|ronin|steadi|crane|weebill|zhiyun|\brs ?[234]\b", re.I)
SAMPLE_FPS = 4
STEADY_MAX = 25.0       # per-sample motion under this = steady (YAVG of frame difference at 480px)
WARP_MAX_MEAN = 55.0    # mean motion above this is beyond what Warp Stabilizer saves
MIN_STEADY_S = 2.5      # a usable b-roll cut
BEST_CUT_S = 5.0        # length of the best cut chosen for Warp (the least-shaky window)
PAD = 0.15


def is_creative(clip: Clip) -> bool:
    return bool(CREATIVE_CAMERAS.search(clip.camera or "") or CREATIVE_CAMERAS.search(clip.rel or ""))


def is_gimbal(clip: Clip, patterns: list[str]) -> bool:
    if GIMBAL_CAMERAS.search(clip.camera or "") or GIMBAL_CAMERAS.search(clip.rel or ""):
        return True
    rel = (clip.rel or clip.path).replace("\\", "/")
    for pat in patterns:
        pat = pat.strip().replace("\\", "/")
        if not pat or pat.startswith("#"):
            continue
        if pat == "*" or pat.lower() in rel.lower() or fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(clip.name, pat):
            return True
    return False


def best_window(motion: list[float], duration: float) -> tuple[float, float, float]:
    """The least-shaky BEST_CUT_S window: (start s, end s, mean motion)."""
    n = len(motion)
    w = max(1, min(n, int(round(BEST_CUT_S * SAMPLE_FPS))))
    acc = sum(motion[:w]); best, best_i = acc, 0
    for i in range(1, n - w + 1):
        acc += motion[i + w - 1] - motion[i - 1]
        if acc < best:
            best, best_i = acc, i
    a = best_i / SAMPLE_FPS
    return round(a, 3), round(min(duration, (best_i + w) / SAMPLE_FPS), 3), best / w


def motion_profile(clip: Clip) -> list[float]:
    r = run(["ffmpeg", "-v", "info", "-nostats", "-hide_banner", "-i", clip.path, "-an", "-vf",
             f"fps={SAMPLE_FPS},scale=480:-2,tblend=all_mode=difference,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-",
             "-f", "null", "-"], check=False)
    # metadata=print:file=- lands on stdout on some ffmpeg builds and stderr on others
    return [float(x) for x in re.findall(r"lavfi\.signalstats\.YAVG=([\d.]+)", (r.stdout or "") + (r.stderr or ""))]


def decide(clip: Clip, motion: list[float], gimbal: bool = False) -> dict:
    n = len(motion)
    if not n:
        return {"name": clip.name, "path": clip.path, "camera": clip.camera, "gimbal": gimbal,
                "decision": "warp" if gimbal else "handheld", "reason": "no motion data"}
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
    out = {"name": clip.name, "path": clip.path, "camera": clip.camera, "gimbal": gimbal,
           "mean_motion": round(mean, 1), "steady_s": round(steady_s, 1)}
    # 1. the best cut first: a steady stretch needs no stabilizing
    if steady_s >= MIN_STEADY_S:
        a = max(0.0, best_start / SAMPLE_FPS + PAD)
        b = min(clip.duration, (best_start + best) / SAMPLE_FPS - PAD)
        out.update(decision="best-cut", range=[round(a, 3), round(b, 3)], reason=f"{steady_s:.1f}s steady stretch")
        return out
    # 2. no steady stretch: the least-shaky cut of the clip
    a, b, wmean = best_window(motion, clip.duration)
    out.update(range=[a, b], best_cut_motion=round(wmean, 1))
    if wmean > WARP_MAX_MEAN:
        out.update(decision="too-shaky", reason=f"best cut still shakes (mean {wmean:.0f}), nothing to save")
    elif gimbal:   # 3. stabilize only gimbal shots, and only the best cut
        out.update(decision="warp", reason=f"gimbal, no steady stretch (longest {steady_s:.1f}s): Warp on the best cut {a:.1f}-{b:.1f}s (mean {wmean:.0f})")
    else:
        out.update(decision="handheld", reason=f"not a gimbal shot, not stabilized; best cut {a:.1f}-{b:.1f}s (mean {wmean:.0f})")
    return out


def steady(clips: list[Clip], cull: list[dict], workers: int = 4, gimbal_patterns: list[str] | None = None) -> dict:
    gimbal_patterns = gimbal_patterns or []
    flagged = {m["path"] for m in cull if "heavy-motion" in (m.get("warn") or []) and not m.get("reject")}
    todo = [c for c in clips if c.kind == "video" and is_creative(c) and c.path in flagged]
    skipped = sum(1 for c in clips if c.kind == "video" and not is_creative(c) and c.path in flagged)
    ng = sum(1 for c in todo if is_gimbal(c, gimbal_patterns))
    log(f"steady: {len(todo)} shaky Creative/Glider clips to judge, {ng} of them gimbal shots ({skipped} shaky clips on other cameras left alone)")
    res = {}
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(motion_profile, c): c for c in todo}
        for i, f in enumerate(cf.as_completed(futs), 1):
            c = futs[f]
            try:
                res[c.path] = decide(c, f.result(), is_gimbal(c, gimbal_patterns))
            except Exception as e:
                g = is_gimbal(c, gimbal_patterns)
                res[c.path] = {"name": c.name, "path": c.path, "camera": c.camera, "gimbal": g, "decision": "warp" if g else "handheld", "reason": f"measure error: {e}"}
            if i % 10 == 0 or i == len(futs):
                log(f"steady {i}/{len(futs)}")
    counts = {k: sum(1 for v in res.values() if v["decision"] == k) for k in ("best-cut", "warp", "handheld", "too-shaky")}
    log(f"steady: {counts['best-cut']} best cuts, {counts['warp']} gimbal shots for Warp Stabilizer, "
        f"{counts['handheld']} not gimbal (not stabilized), {counts['too-shaky']} too shaky")
    return res
