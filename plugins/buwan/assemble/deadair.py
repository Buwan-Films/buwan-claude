"""Dead air: find the speech inside speech clips and drop the silence.

For every clip in the Speech category: silencedetect -> kept ranges (speech, padded).
Used three ways:
  - organize: kept ranges become Favorite ranges on the clip (dead air shows unfavorited, skimmable).
  - aroll:    an "A-Roll clean" project = every speech clip in order with silences cut out, speaker markers,
              enhancement applied. The Plotline-style timeline to read the day from.
  - plot:     transcription runs on the kept ranges only (faster, cleaner).
"""
from __future__ import annotations

import concurrent.futures as cf
import re
import subprocess

from common import Clip, log, save_json, load_json

NOISE_DB = -38      # below this is silence
MIN_SILENCE = 0.9   # seconds of silence that count as dead air
PAD = 0.25          # keep this much around speech
MIN_KEEP = 0.8      # drop speech islands shorter than this


def speech_ranges(clip: Clip, noise_db=NOISE_DB, min_sil=MIN_SILENCE) -> list[list[float]]:
    r = subprocess.run(["ffmpeg", "-v", "info", "-nostats", "-hide_banner", "-i", clip.path, "-vn", "-af",
                        f"highpass=f=100,silencedetect=n={noise_db}dB:d={min_sil}", "-f", "null", "-"], capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: (-?[\d.]+)", r.stderr)]
    sil = []
    for s in starts:
        e = next((e for e in ends if e > s), clip.duration)
        sil.append((max(0.0, s), min(clip.duration, e)))
    # complement = speech
    keep, pos = [], 0.0
    for s, e in sil:
        if s - pos > 0:
            keep.append([pos, s])
        pos = e
    if clip.duration - pos > 0:
        keep.append([pos, clip.duration])
    # pad and merge
    out = []
    for a, b in keep:
        a, b = max(0.0, a - PAD), min(clip.duration, b + PAD)
        if out and a <= out[-1][1]:
            out[-1][1] = b
        else:
            out.append([a, b])
    return [[round(a, 3), round(b, 3)] for a, b in out if b - a >= MIN_KEEP]


def dead_air(clips: list[Clip], workers=4) -> dict:
    res = {}
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(speech_ranges, c): c for c in clips if c.has_audio}
        for i, f in enumerate(cf.as_completed(futs), 1):
            c = futs[f]
            try:
                rng = f.result()
            except Exception as e:
                rng, err = [], str(e)
            kept = sum(b - a for a, b in rng)
            res[c.path] = {"ranges": rng, "kept_s": round(kept, 1), "removed_s": round(c.duration - kept, 1)}
            if i % 10 == 0 or i == len(futs):
                log(f"dead air {i}/{len(futs)}")
    return res


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("clips_json"); ap.add_argument("out_json")
    a = ap.parse_args()
    clips = [Clip.from_json(d) for d in load_json(a.clips_json)]
    res = dead_air(clips)
    save_json(a.out_json, res)
    log(f"kept {sum(v['kept_s'] for v in res.values())/60:.1f} min, removed {sum(v['removed_s'] for v in res.values())/60:.1f} min of dead air")
