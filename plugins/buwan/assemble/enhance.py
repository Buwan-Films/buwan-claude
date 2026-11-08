"""Sound enhancement for speech clips — measured, then applied two ways:

1. Native, non-destructive (Final Cut): per-clip recipe written into the FCPXML as
   <audio-channel-source> adjustments: loudness, noise reduction, voice EQ, voice isolation.
2. Rendered (any app, optional): a cleaned WAV per speech clip in edit/audio/clean/ —
   high-pass 80 Hz, FFT denoise, loudness to -17 LUFS, true peak -6 dBTP — for Premiere / Resolve
   editors to lay under the picture (sources are never modified).

The recipe is driven by measurements: integrated loudness, noise floor (quietest 10%), peak.
"""
from __future__ import annotations

import concurrent.futures as cf
import re
import subprocess
from pathlib import Path

from common import Clip, log, save_json, load_json

TARGET_LUFS = -17.0
TARGET_TP = -6.0


def measure_audio(path: str) -> dict:
    r = subprocess.run(["ffmpeg", "-v", "info", "-nostats", "-hide_banner", "-i", path, "-vn", "-af",
                        "ebur128=peak=true,astats=metadata=1:reset=1:length=0.5,ametadata=print:key=lavfi.astats.Overall.RMS_level:file=-",
                        "-f", "null", "-"], capture_output=True, text=True)
    out = r.stdout + r.stderr
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", out)
    tp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", out)
    rms = [float(x) for x in re.findall(r"lavfi\.astats\.Overall\.RMS_level=(-?[\d.]+)", out) if x not in ("-inf", "inf")]
    rms = sorted(v for v in rms if v > -90)
    floor = rms[int(len(rms) * 0.1)] if rms else -90.0
    loud = rms[int(len(rms) * 0.8)] if rms else -30.0
    return {"lufs": float(lufs[-1]) if lufs else None, "true_peak": float(tp[-1]) if tp else None,
            "noise_floor_db": round(floor, 1), "speech_level_db": round(loud, 1), "snr_db": round(loud - floor, 1)}


def recipe(m: dict) -> dict:
    """FCP enhancement amounts (0-100) from the measurements."""
    snr = m.get("snr_db") or 30
    lufs = m.get("lufs") if m.get("lufs") is not None else -30
    gain_needed = TARGET_LUFS - lufs
    rec = {
        # Loudness: amount ~ how hard to push toward the target; uniformity evens out levels within the clip
        "loudness_amount": int(max(0, min(100, 40 + gain_needed * 4))),
        "loudness_uniformity": 30 if snr > 25 else 15,
        "noise_reduction": 0 if snr > 35 else 25 if snr > 25 else 50 if snr > 15 else 75,
        "voice_isolation": 0 if snr > 20 else 40 if snr > 12 else 70,
        "eq": "voice_enhance",
        "gain_db": round(max(-12.0, min(12.0, gain_needed)), 1),
    }
    rec["notes"] = []
    if snr < 12:
        rec["notes"].append("very noisy — consider the lav/recorder file if one exists")
    if m.get("true_peak") is not None and m["true_peak"] > -1:
        rec["notes"].append("clipping in the source")
    return rec


def enhance(clips: list[Clip], workers=4) -> dict:
    out = {}
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(measure_audio, c.path): c for c in clips if c.has_audio}
        for i, f in enumerate(cf.as_completed(futs), 1):
            c = futs[f]
            try:
                m = f.result()
            except Exception as e:
                m = {"error": str(e)}
            out[c.path] = {"measure": m, "recipe": recipe(m) if "error" not in m else None}
            if i % 10 == 0 or i == len(futs):
                log(f"enhance {i}/{len(futs)}")
    return out


def render_clean(clip: Clip, m: dict, out_dir: Path) -> str:
    out_dir.mkdir(parents=True, exist_ok=True)
    # name by the clip's path: cameras and card folders reuse file names (C0001...), so the bare name collides
    rel = Path(clip.rel or f"{clip.camera}/{clip.name}").with_suffix("")
    stem = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in "_".join(rel.parts))
    out = out_dir / f"{stem}_clean.wav"
    snr = m.get("snr_db") or 30
    nr = "" if snr > 35 else f"afftdn=nf={max(-80, min(-20, (m.get('noise_floor_db') or -60) - 5)):.0f}:nr={12 if snr > 20 else 20},"
    af = f"highpass=f=80,{nr}loudnorm=I={TARGET_LUFS}:TP={TARGET_TP}:LRA=9,alimiter=limit={TARGET_TP}dB:level=disabled"   # level=disabled: alimiter auto-levels to 0 dBFS by default
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", clip.path, "-vn", "-af", af, "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le", str(out)], check=True)
    return str(out)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("clips_json"); ap.add_argument("out_json"); ap.add_argument("--render-dir")
    a = ap.parse_args()
    clips = [Clip.from_json(d) for d in load_json(a.clips_json)]
    res = enhance(clips)
    if a.render_dir:
        for c in clips:
            if c.path in res and res[c.path]["recipe"]:
                res[c.path]["clean"] = render_clean(c, res[c.path]["measure"], Path(a.render_dir))
    save_json(a.out_json, res)
