"""Cull: measure every clip and flag the unusable ones. Nothing is deleted — flags only.

Reject reasons (clip is marked Rejected in the editing app):
  false-start   shorter than MIN_SEC
  black         mostly black frames
  blown         mostly clipped-white frames
  silent-dead   video with no usable picture AND no audio
Warnings (kept, but noted in the clip log):
  dark / bright     average luma outside the usable range
  soft-focus        low sharpness most of the time
  heavy-motion      sustained frame-to-frame change (shake / whip)
  frozen            long frozen sections
  low-audio         audio under -45 LUFS (unusable for speech)
"""
from __future__ import annotations

import concurrent.futures as cf
import re
import sys
from pathlib import Path

from common import Clip, log, run, save_json, load_json

MIN_SEC = 1.0
SAMPLE_FPS = 4          # frames per second analysed
SCALE_W = 480           # analysis width


def _ff(path, vf, extra=None, audio=False):
    cmd = ["ffmpeg", "-v", "info", "-nostats", "-hide_banner", "-i", str(path)]
    if audio:
        cmd += ["-vn", "-af", vf, "-f", "null", "-"]
    else:
        cmd += ["-an", "-vf", vf, "-f", "null", "-"]
    r = run(cmd, check=False)
    return r.stderr


def measure(clip: Clip) -> dict:
    m = {"name": clip.name, "path": clip.path, "reject": [], "warn": [], "metrics": {}}
    if clip.duration < MIN_SEC:
        m["reject"].append("false-start")
        return m
    if clip.kind == "video":
        # Two passes at 4 fps / 480px: picture quality, then frame-to-frame motion.
        err1 = _ff(clip.path, f"fps={SAMPLE_FPS},scale={SCALE_W}:-2,blackdetect=d=0.5:pic_th=0.97:pix_th=0.10,freezedetect=n=-50dB:d=3,blurdetect=block_pct=80,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-")
        err2 = _ff(clip.path, f"fps={SAMPLE_FPS},scale={SCALE_W}:-2,tblend=all_mode=difference,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-")
        yavg = [float(x) for x in re.findall(r"lavfi\.signalstats\.YAVG=([\d.]+)", err1)]
        motion = [float(x) for x in re.findall(r"lavfi\.signalstats\.YAVG=([\d.]+)", err2)]
        blur = [float(x) for x in re.findall(r"lavfi\.blur=([\d.]+)", err1)]
        black = sum(float(d) for d in re.findall(r"black_duration:([\d.]+)", err1))
        frozen = sum(float(d) for d in re.findall(r"freeze_duration: ([\d.]+)", err1))
        if not frozen:
            starts = [float(x) for x in re.findall(r"lavfi\.freezedetect\.freeze_start: ([\d.]+)", err1)]
            ends = [float(x) for x in re.findall(r"lavfi\.freezedetect\.freeze_end: ([\d.]+)", err1)]
            frozen = sum(e - s for s, e in zip(starts, ends))
        n = max(1, len(yavg))
        mean_y = sum(yavg) / n if yavg else 0
        dark_share = sum(1 for y in yavg if y < 16) / n
        bright_share = sum(1 for y in yavg if y > 235) / n
        mot = sorted(motion)
        p75_motion = mot[int(0.75 * (len(mot) - 1))] if mot else 0
        high_motion_share = sum(1 for v in motion if v > 40) / max(1, len(motion))
        blur_sorted = sorted(blur)
        med_blur = blur_sorted[len(blur_sorted) // 2] if blur_sorted else 0
        m["metrics"].update(dict(mean_luma=round(mean_y, 1), black_sec=round(black, 1), frozen_sec=round(frozen, 1),
                                 p75_motion=round(p75_motion, 1), high_motion_share=round(high_motion_share, 2), median_blur=round(med_blur, 2)))
        if black >= 0.8 * clip.duration or dark_share >= 0.9:
            m["reject"].append("black")
        if bright_share >= 0.9:
            m["reject"].append("blown")
        if not m["reject"]:
            if mean_y < 28:
                m["warn"].append("dark")
            elif mean_y > 215:
                m["warn"].append("bright")
            if high_motion_share > 0.5:
                m["warn"].append("heavy-motion")
            if frozen >= 0.6 * clip.duration and clip.duration > 4:
                m["warn"].append("frozen")
            # blurdetect: higher = blurrier; threshold tuned loosely, it's a hint not a verdict
            if med_blur and med_blur > 9:
                m["warn"].append("soft-focus")
    if clip.has_audio:
        err = _ff(clip.path, "ebur128=peak=true", audio=True)
        lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", err)
        peak = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", err)
        if lufs:
            I = float(lufs[-1])
            m["metrics"]["lufs"] = I
            m["metrics"]["peak_dbfs"] = float(peak[-1]) if peak else None
            if I < -45:
                m["warn"].append("low-audio")
                if "black" in m["reject"]:
                    m["reject"].append("silent-dead")
    else:
        m["metrics"]["lufs"] = None
    return m


def cull(clips: list[Clip], workers: int = 4, progress=True) -> list[dict]:
    out = []
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(measure, c): c for c in clips}
        for i, f in enumerate(cf.as_completed(futs), 1):
            try:
                out.append(f.result())
            except Exception as e:
                c = futs[f]
                out.append({"name": c.name, "path": c.path, "reject": [], "warn": [f"measure-error:{e}"], "metrics": {}})
            if progress and (i % 10 == 0 or i == len(clips)):
                log(f"cull {i}/{len(clips)}")
    by = {m["path"]: m for m in out}
    return [by[c.path] for c in clips]


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("clips_json")
    ap.add_argument("out_json")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    clips = [Clip.from_json(d) for d in load_json(a.clips_json)]
    res = cull(clips, a.workers)
    save_json(a.out_json, res)
    rej = sum(1 for r in res if r["reject"])
    log(f"culled {len(res)} clips: {rej} rejected, {sum(1 for r in res if r['warn'])} with warnings")
