"""Speech moments: the angles of one interview / vows / speech, synced, on the one best audio, dead air out.

The editor names the moment and lists its clips (any cameras, plus a lav/recorder file if there is one):
  1. best     each clip's audio is measured (signal-to-noise, clipping, level); the best one carries the moment
              (a sound-only file wins a tie: lavs and recorders are cleaner)
  2. sync     every other clip is placed against the best audio by its sound (onset envelopes, cross-correlation at
              20 ms, refined to 2.5 ms), so wrong camera clocks don't matter. A clip with no usable sound can't be
              synced: it is listed for the editor to place by hand
  3. clean    high-pass, noise reduction scaled to the noise, voice EQ, levelled
  4. dead air silences between words found on the clean audio; the same cuts on every angle, so they stay in sync
              (words are never cut: vows and speeches stay verbatim)
  5. render   each video angle: the kept ranges, the exposure fix (exposure.json, or measured now), no grade,
              HEVC 10-bit, the one clean audio at -17 LUFS / peaks -6 dBFS. Each angle holds only what it covered
              and starts at the timecode of where that sits in the cut moment (the moment starts at 00:00:00:00),
              so the multicam is built by timecode in any app.
Output: <raw>_SPEECH_<YYYYMMDD-HHMM>/<INTERVIEWS|VOWS|SPEECHES>/<moment>/<camera>_<clip>.mov + <moment>_audio.wav
        + moment.json. The raw files are only read.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from scipy.signal import fftconvolve

from common import Clip, log, probe_clip
from deadair import speech_ranges
from render import _encode_args, _grade_chain, _run, ffmpeg_bin

TYPES = {"interview": "INTERVIEWS", "interviews": "INTERVIEWS", "vows": "VOWS", "vow": "VOWS",
         "speech": "SPEECHES", "speeches": "SPEECHES"}
COARSE_HZ, FINE_HZ = 50, 400
MIN_CONF = 3.0
SILENT_DB = -50.0        # speech level under this: no usable audio on that clip
FADE = 0.02
TARGET_LUFS, TARGET_TP = -17.0, -6.0


# ---------- 1. sync ----------
def _envelope(path: str, hz: int, sr: int = 8000) -> np.ndarray:
    import sync
    sync.MIN_RMS_DB = -85.0   # a far-away camera mic is quiet but still carries the timing of the words
    return sync.envelope(path, hz=hz, sr=sr if hz <= 100 else 16000)


def _offset(ref_env: np.ndarray, env: np.ndarray, hz: int) -> tuple[float | None, float]:
    """Start of `env` on the ref timeline, in seconds (may be negative), and a confidence (z above chance)."""
    if len(env) < hz * 2 or len(ref_env) < hz * 2:
        return None, 0.0
    c = fftconvolve(ref_env, env[::-1], mode="full")   # index k <-> lag k - (len(env) - 1)
    k = int(np.argmax(c))
    sd = float(np.std(c))
    if sd < 1e-9:
        return None, 0.0
    conf = float((c[k] - np.mean(c)) / sd) - float(np.sqrt(2 * np.log(len(c))))
    return (k - (len(env) - 1)) / hz, conf


def _refine(ref_path: str, path: str, coarse: float) -> float:
    a, b = _envelope(ref_path, FINE_HZ), _envelope(path, FINE_HZ)
    best, best_v = coarse, -np.inf
    base = int(round(coarse * FINE_HZ))
    for d in range(-int(0.06 * FINE_HZ), int(0.06 * FINE_HZ) + 1):
        lag = base + d
        i0, j0 = max(0, lag), max(0, -lag)
        n = min(len(a) - i0, len(b) - j0)
        if n < FINE_HZ:
            continue
        v = float(np.dot(a[i0:i0 + n], b[j0:j0 + n]) / n)
        if v > best_v:
            best, best_v = lag / FINE_HZ, v
    return best


# ---------- 2. best audio ----------
def _measure(path: str, start: float, dur: float) -> dict:
    import re
    r = subprocess.run(["ffmpeg", "-v", "info", "-nostats", "-hide_banner", "-ss", f"{max(0.0, start):.3f}", "-t", f"{dur:.3f}",
                        "-i", path, "-vn", "-af", "highpass=f=80,ebur128=peak=true,astats=metadata=1:reset=1:length=0.5,"
                        "ametadata=print:key=lavfi.astats.Overall.RMS_level:file=-", "-f", "null", "-"], capture_output=True, text=True)
    out = r.stdout + r.stderr
    tp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", out)
    rms = sorted(float(x) for x in re.findall(r"lavfi\.astats\.Overall\.RMS_level=(-?[\d.]+)", out) if x not in ("-inf", "inf") and float(x) > -90)
    floor = rms[int(len(rms) * 0.1)] if rms else -90.0
    loud = rms[int(len(rms) * 0.8)] if rms else -90.0
    return {"speech_level_db": round(loud, 1), "noise_floor_db": round(floor, 1), "snr_db": round(loud - floor, 1),
            "true_peak": float(tp[-1]) if tp else None}


def _score(m: dict, sound_only: bool) -> float:
    if m["speech_level_db"] < SILENT_DB:
        return -1e9
    s = m["snr_db"]
    if m.get("true_peak") is not None and m["true_peak"] > -0.5:
        s -= 8          # clipped
    return s + (3 if sound_only else 0)


# ---------- 3. clean, 4. dead air ----------
def _clean(ff: str, path: str, start: float, dur: float, m: dict, out: Path) -> None:
    snr = m["snr_db"]
    nr = "" if snr > 35 else f"afftdn=nf={max(-80, min(-20, m['noise_floor_db'] - 5)):.0f}:nr={12 if snr > 20 else 20},"
    pre = f"adelay={int(-start * 1000)}:all=1," if start < 0 else ""   # the best audio starts after the moment: pad its head
    af = (f"{pre}highpass=f=80,{nr}equalizer=f=250:t=q:w=1.2:g=-2,equalizer=f=3500:t=q:w=1.0:g=2,"
          f"loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=11,alimiter=limit={TARGET_TP}dB:level=disabled,apad")
    _run([ff, "-v", "error", "-y", "-ss", f"{max(0.0, start):.3f}", "-i", path, "-vn", "-af", af, "-t", f"{dur:.3f}",
          "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le", str(out)])


def _cut_audio(ff: str, clean: Path, ranges: list, out: Path) -> None:
    fc = []
    for i, (a, b) in enumerate(ranges):
        fo = max(0.0, (b - a) - FADE)
        fc.append(f"[0:a]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS,afade=t=in:d={FADE},afade=t=out:st={fo:.3f}:d={FADE}[a{i}]")
    fc.append("".join(f"[a{i}]" for i in range(len(ranges))) + f"concat=n={len(ranges)}:v=0:a=1[ac]")
    # re-level what is left (dead air gone): aim 1 LU hot into the -6 dB limiter, lands at -17
    fc.append(f"[ac]loudnorm=I={TARGET_LUFS + 1:.1f}:TP=-1.5:LRA=11,alimiter=limit={TARGET_TP}dB:level=disabled,aresample=48000[ao]")
    _run([ff, "-v", "error", "-y", "-i", str(clean), "-filter_complex", ";".join(fc), "-map", "[ao]",
          "-ac", "2", "-c:a", "pcm_s24le", str(out)])


# ---------- 5. render an angle ----------
def _timecode(seconds: float, fps_num: int, fps_den: int) -> str:
    """Non-drop timecode for a start this far into the moment (same scheme for every angle, so they line up)."""
    fps = fps_num / fps_den if fps_num else 30000 / 1001
    base = int(round(fps))
    f = int(round(seconds * fps))
    return f"{f // (base * 3600):02d}:{f // (base * 60) % 60:02d}:{f // base % 60:02d}:{f % base:02d}"


def _render_angle(ff: str, c: Clip, off: float, ranges: list, ev: float, audio: Path, out: Path) -> dict:
    """Kept ranges are on the moment timeline; this angle's source time = moment time - off.
    The angle holds only what it covered (no black head or tail) and starts at the timecode of where that sits
    in the cut moment, so every app builds the multicam by timecode."""
    w, h = c.width or 1920, c.height or 1080
    rate = f"{c.fps_num}/{c.fps_den}" if c.fps_num else "30000/1001"
    norm = f"scale={w}:{h},setsar=1,fps={rate},format=yuv420p10le"
    pos, first, last, pics = 0.0, None, None, []
    for a, b in ranges:
        sa, sb = a - off, b - off                       # this range in the angle's own time
        lo, hi = max(sa, 0.0), min(sb, c.duration)
        if hi - lo > 0.04:
            t0 = pos + (lo - sa)                        # where this piece sits on the cut timeline
            if first is None:
                first = t0
            last = t0 + (hi - lo)
            pics.append((lo, hi))
        pos += b - a
    if not pics:
        return {"skipped": "this angle only covered dead air"}
    fc = [f"[0:v]trim=start={lo:.3f}:end={hi:.3f},setpts=PTS-STARTPTS,{norm}[p{i}]" for i, (lo, hi) in enumerate(pics)]
    fc.append("".join(f"[p{i}]" for i in range(len(pics))) + f"concat=n={len(pics)}:v=1:a=0[vc]")
    fc.append(f"[vc]{_grade_chain(ev, None)}[vo]")
    fc.append(f"[1:a]atrim=start={first:.4f}:end={last:.4f},asetpts=PTS-STARTPTS[ao]")
    tc = _timecode(first, c.fps_num, c.fps_den)
    tmp = out.with_name(out.stem + ".part.mov")
    _run([ff, "-v", "error", "-y", "-i", c.path, "-i", str(audio), "-filter_complex", ";".join(fc),
          "-map", "[vo]", "-map", "[ao]", "-c:a", "aac", "-b:a", "320k", "-timecode", tc] + _encode_args(tmp))
    tmp.rename(out)
    return {"timecode": tc, "starts_s": round(first, 3), "length_s": round(last - first, 3),
            "done": f"exposure {ev:+.2f} EV" if ev else "exposure ok"}


def _exposure_ev(c: Clip, expo: dict, key: str) -> tuple[float, str]:
    if key in expo:
        return expo[key].get("ev") or 0.0, "exposure.json"
    from exposure import decide, load_band, measure
    d = decide(measure(c), load_band("warm"))
    return d["ev"], "measured now"


def run_moment(project: Path, moment: dict, source: Path, raw_copy: Path, out_root: Path, workers: int = 3) -> dict:
    ff = ffmpeg_bin()
    kind = TYPES[moment["type"].lower()]
    name = moment["name"]
    mdir = out_root / kind / "".join(ch if ch not in '/\\:' else "-" for ch in name)
    mdir.mkdir(parents=True, exist_ok=True)
    expo_p = project / "edit" / "assemble" / "exposure.json"
    expo = json.loads(expo_p.read_text()) if expo_p.exists() else {}

    clips = []
    for p in moment["clips"]:
        path = Path(p) if os.path.isabs(p) else source / p
        if not path.exists():
            raise FileNotFoundError(f"{name}: {p} not found (give it relative to {source} or as a full path)")
        c = probe_clip(path, source)
        if c:
            clips.append(c)
    if not clips:
        raise ValueError(f"{name}: no clips")
    log(f"speech: {kind}/{name}: {len(clips)} clips")

    # 2 before 1: measure every clip's sound; the best one carries the moment and is what the angles sync to
    meas = {c.path: _measure(c.path, 0.0, c.duration) | {"sound_only": c.kind == "audio"} for c in clips if c.has_audio}
    if not meas:
        raise ValueError(f"{name}: none of the clips has sound (find the lav/recorder file and add it)")
    best = max(meas, key=lambda p: _score(meas[p], meas[p]["sound_only"]))
    if _score(meas[best], meas[best]["sound_only"]) < -1e8:
        raise ValueError(f"{name}: every clip's audio is silent (find the lav/recorder file and add it)")
    bc = next(c for c in clips if c.path == best)

    # 1. sync every other clip to the best audio by sound
    ref_env = _envelope(best, COARSE_HZ)
    place = {best: {"offset": 0.0, "conf": None, "how": "best audio (reference)"}}
    for c in clips:
        if c.path == best:
            continue
        if not c.has_audio:   # a quiet camera mic still syncs (the envelope is level-free); only no audio at all can't
            place[c.path] = {"offset": None, "how": "no sound on this clip: can't sync it, place it by hand"}
            continue
        off, conf = _offset(ref_env, _envelope(c.path, COARSE_HZ), COARSE_HZ)
        if off is None or conf < MIN_CONF:
            place[c.path] = {"offset": None, "conf": round(conf, 1), "how": "no audio match: left out, check it's the same moment"}
            continue
        place[c.path] = {"offset": round(_refine(best, c.path, off), 4), "conf": round(conf, 1), "how": "synced by sound"}
    synced = [c for c in clips if place[c.path]["offset"] is not None]

    # the moment = where the best audio runs (that's where the words are)
    m0, m1 = place[best]["offset"], place[best]["offset"] + bc.duration
    dur = m1 - m0
    clean = mdir / ".clean_full.wav"
    _clean(ff, bc.path, 0.0, dur, meas[best], clean)

    # 4. dead air on the clean audio (moment-relative times)
    probe = Clip(path=str(clean), name="clean", kind="audio", duration=dur, has_audio=True)
    ranges = speech_ranges(probe)
    if not ranges:
        ranges = [[0.0, round(dur, 3)]]
    kept = sum(b - a for a, b in ranges)
    audio = mdir / f"{mdir.name}_audio.wav"
    _cut_audio(ff, clean, ranges, audio)
    clean.unlink(missing_ok=True)

    # 5. every video angle, the same cuts (moment time -> angle time = t + m0 - offset)
    angles = []
    import concurrent.futures as cf

    def one(c):
        rel = os.path.relpath(c.path, source)
        key = str(raw_copy / rel)
        ev, how = _exposure_ev(c, expo, key)
        out = mdir / f"{c.camera or 'cam'}_{c.name}.mov".replace(" ", "-")
        r = _render_angle(ff, c, place[c.path]["offset"] - m0, ranges, ev, audio, out)
        return {"angle": out.name if "skipped" not in r else None, "source": c.path, "offset_s": place[c.path]["offset"],
                "exposure_ev": ev, "exposure_from": how} | r

    vids = [c for c in synced if c.kind == "video"]
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        angles = list(ex.map(one, vids))
    res = {"moment": name, "type": kind, "folder": str(mdir), "best_audio": best, "audio": audio.name,
           "audio_measure": meas, "speech_kept_s": round(kept, 1), "dead_air_removed_s": round(max(0.0, dur - kept), 1),
           "ranges": ranges, "placement": place, "angles": angles,
           "left_out": [{"clip": c.path, "why": place[c.path]["how"]} for c in clips if place[c.path]["offset"] is None]}
    (mdir / "moment.json").write_text(json.dumps(res, indent=2))
    log(f"speech: {kind}/{name}: {len(angles)} angles, best audio {Path(best).name}, "
        f"{kept / 60:.1f} min kept, {(dur - kept) / 60:.1f} min dead air out"
        + (f", {len(res['left_out'])} left out" if res["left_out"] else ""))
    return res


def run(project: Path, moments: list[dict], source: Path, raw_copy: Path, out: Path | None, workers: int = 3) -> dict:
    out = out or source.parent / f"{source.name}_SPEECH_{_dt.datetime.now():%Y%m%d-%H%M}"
    out.mkdir(parents=True, exist_ok=True)
    done, failed = [], []
    for m in moments:
        try:
            done.append(run_moment(project, m, source, raw_copy, out, workers))
        except Exception as e:
            log(f"speech: FAILED {m.get('name')}: {e}")
            failed.append({"moment": m.get("name"), "error": str(e)})
    (out / "speech_log.json").write_text(json.dumps({"done": done, "failed": failed}, indent=2))
    log(f"speech: {len(done)} moments done, {len(failed)} failed -> {out}")
    return {"out": str(out), "done": len(done), "failed": len(failed)}
