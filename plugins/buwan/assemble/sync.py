"""Multicam sync by audio.

Every clip's audio is reduced to an onset envelope. One camera's clips (the "anchor", normally the camera that
rolled longest on the ceremony) are laid on a master timeline by their timestamps; every other clip is placed by
cross-correlating its envelope against the master. Cameras with a wrong clock still sync, because the match is
on sound, not on time of day. Output: an offset (seconds on the master timeline) and a confidence per clip.
"""
from __future__ import annotations

import subprocess
from datetime import datetime, timezone

import numpy as np
from scipy.signal import fftconvolve

from common import Clip, log, save_json, load_json

ENV_HZ = 50          # envelope rate for the coarse search (20 ms)
FINE_HZ = 400        # refine rate (2.5 ms)
MIN_CONF = 3.0       # peak z-score above the expected noise maximum, sqrt(2 ln N), to accept a match
MIN_R = 0.4          # a candidate offset is accepted only if the envelopes actually correlate (Pearson r) over the overlap
MIN_OVERLAP_S = 5.0  # ... measured over at least this much overlap with anchor audio
TOP_K = 8            # candidate offsets checked per clip
MIN_RMS_DB = -55.0   # quieter than this there is nothing to match on: clip stays unsynced / timestamp


def _audio(path, sr):
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True)
    if p.returncode != 0:
        return np.zeros(0, dtype=np.float32)
    return np.frombuffer(p.stdout, dtype=np.float32).copy()


def envelope(path, hz=ENV_HZ, sr=8000):
    """Spectral-flux onset envelope summed over 6 bands (robust to level differences between cameras)."""
    y = _audio(path, sr)
    if not len(y):
        return np.zeros(0, dtype=np.float32)
    rms = float(np.sqrt(np.mean(np.square(y, dtype=np.float64))))
    if rms <= 0 or 20 * np.log10(rms) < MIN_RMS_DB:
        return np.zeros(0, dtype=np.float32)  # near-silent (e.g. slow-mo): no sound to sync on
    step = sr // hz
    n = len(y) // step
    if n < 2:
        return np.zeros(0, dtype=np.float32)
    frames = y[: n * step].reshape(n, step) * np.hanning(step)
    spec = np.abs(np.fft.rfft(frames, axis=1)) + 1e-6
    edges = np.geomspace(60, sr / 2 - 1, 7)
    freqs = np.fft.rfftfreq(step, 1 / sr)
    bands = np.stack([spec[:, (freqs >= lo) & (freqs < hi)].sum(axis=1) for lo, hi in zip(edges[:-1], edges[1:])], axis=1)
    logb = np.log(bands + 1e-6)
    flux = np.maximum(np.diff(logb, axis=0, prepend=logb[:1]), 0).sum(axis=1)
    flux -= flux.mean()
    s = flux.std()
    return (flux / s).astype(np.float32) if s > 0 else flux.astype(np.float32)


def _parse_time(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc).timestamp()
    except Exception:
        return None


def correlate(master: np.ndarray, probe: np.ndarray, hz: int, search: tuple[float, float] | None = None):
    """Return (offset_seconds, confidence) of probe inside master."""
    if len(probe) < hz * 2 or len(master) < len(probe):
        return None, 0.0
    c = fftconvolve(master, probe[::-1], mode="valid")  # c[k] = sum master[k+i]*probe[i]
    if search:
        lo = max(0, int(search[0] * hz))
        hi = min(len(c), int(search[1] * hz) + 1)
        if hi - lo < 2:
            return None, 0.0
        seg = c[lo:hi]
        k = lo + int(np.argmax(seg))
    else:
        k = int(np.argmax(c))
    # Confidence = how far the peak stands above what pure chance gives over this many lags.
    # (The old peak/median ratio exploded to ~1e8 on silent envelopes and passed ~7 on random noise.)
    pool = c[lo:hi] if search else c
    sd = float(np.std(pool))
    if not np.isfinite(sd) or sd < 1e-6:
        return None, 0.0
    z = float((c[k] - np.mean(pool)) / sd)
    conf = z - float(np.sqrt(2 * np.log(max(len(pool), 2))))
    return k / hz, conf


def _candidates(master, probe, hz, k=TOP_K, sep_s=2.0):
    """Top-k correlation peaks (offsets in samples), at least sep_s apart."""
    if len(probe) < hz * 2 or len(master) < len(probe):
        return []
    c = fftconvolve(master, probe[::-1], mode="valid")
    out, c = [], c.copy()
    sep = int(sep_s * hz)
    for _ in range(k):
        i = int(np.argmax(c))
        if not np.isfinite(c[i]) or c[i] <= 0:
            break
        out.append(i)
        c[max(0, i - sep):i + sep + 1] = -np.inf
    return out


def _verify(master, cover, probe, k, hz):
    """Pearson r between the probe and the anchor audio it would sit on, over the covered overlap."""
    n = min(len(probe), len(master) - k)
    if n <= 0:
        return 0.0
    m = cover[k:k + n]
    if m.sum() < MIN_OVERLAP_S * hz:
        return 0.0
    a, b = master[k:k + n][m], probe[:n][m]
    if a.std() < 1e-6 or b.std() < 1e-6:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


def sync(clips: list[Clip], anchor_camera: str | None = None, trusted_cameras: list[str] | None = None, exclude: set | None = None) -> dict:
    exclude = exclude or set()
    vids = [c for c in clips if c.has_audio and c.duration >= 2 and c.path not in exclude]
    cams = sorted({c.camera for c in vids})
    if not vids:
        return {"anchor": None, "clips": {}}
    # pick anchor: camera with most total duration unless given
    if not anchor_camera:
        tot = {cam: sum(c.duration for c in vids if c.camera == cam) for cam in cams}
        anchor_camera = max(tot, key=tot.get)
    trusted = set(trusted_cameras or [anchor_camera])
    anchor = [c for c in vids if c.camera == anchor_camera]
    times = {c.path: _parse_time(c.created) for c in vids}
    stamped = [c for c in anchor if times[c.path] is not None]
    if not stamped:
        # no timestamps on the anchor camera at all: lay its clips back to back in file order
        t = 0.0
        for c in sorted(anchor, key=lambda x: x.rel):
            times[c.path] = t
            t += c.duration + 1.0
    else:
        # anchor clips without a timestamp follow the previous stamped clip in file order
        prev_end = None
        for c in sorted(anchor, key=lambda x: x.rel):
            if times[c.path] is None:
                times[c.path] = (prev_end + 1.0) if prev_end is not None else min(times[x.path] for x in stamped)
            prev_end = times[c.path] + c.duration
    t0 = min(times[c.path] for c in anchor)
    # master timeline: anchor clips at their timestamps
    placed = {}
    for c in anchor:
        placed[c.path] = {"offset": times[c.path] - t0, "conf": 99.0, "how": "anchor"}
    span = max(v["offset"] + c.duration for c, v in ((c, placed[c.path]) for c in anchor)) + 60
    log(f"sync: anchor={anchor_camera} ({len(anchor)} clips, span {span/60:.1f} min); envelopes...")
    master = np.zeros(int(span * ENV_HZ) + ENV_HZ, dtype=np.float32)
    cover = np.zeros(len(master), dtype=bool)
    envs = {}
    for c in anchor:
        e = envelope(c.path)
        envs[c.path] = e
        k = int(placed[c.path]["offset"] * ENV_HZ)
        master[k:k + len(e)] += e[: len(master) - k]
        cover[k:k + len(e)] = True
    others = [c for c in vids if c.camera != anchor_camera]
    for i, c in enumerate(others, 1):
        e = envelope(c.path)
        envs[c.path] = e
        search = None
        if c.camera in trusted and times[c.path] is not None:
            guess = times[c.path] - t0
            search = (guess - 120, guess + 120)
        # Candidates: the trusted-clock window first (if any), then the top peaks over the whole day.
        # Each one is checked against the anchor audio it would sit on; the best verified one wins.
        cands = []
        if search:
            o, _ = correlate(master, e, ENV_HZ, search)
            if o is not None:
                cands.append(int(round(o * ENV_HZ)))
        cands += _candidates(master, e, ENV_HZ)
        best_r, off = 0.0, None
        for k in cands:
            r = _verify(master, cover, e, k, ENV_HZ)
            if r > best_r:
                best_r, off = r, k / ENV_HZ
        conf = round(best_r * 100, 1)  # stored as r x 100
        if off is not None and best_r >= MIN_R:
            # refine around the coarse offset at FINE_HZ using the best-overlapping anchor clip
            best = max(anchor, key=lambda a: min(placed[a.path]["offset"] + a.duration, off + c.duration) - max(placed[a.path]["offset"], off))
            a_env = envelope(best.path, FINE_HZ)
            p_env = envelope(c.path, FINE_HZ)
            rel = off - placed[best.path]["offset"]
            if len(a_env) and len(p_env):
                lo, hi = rel - 1.0, rel + 1.0
                if lo < 0:  # probe starts before the anchor clip: trim probe
                    cut = int(-lo * FINE_HZ)
                    p_env2 = p_env[cut:] if cut < len(p_env) else p_env
                    off_f, conf_f = correlate(a_env, p_env2[: len(a_env)] if len(p_env2) > len(a_env) else p_env2, FINE_HZ, (0, 2.0))
                    if off_f is not None and conf_f > 1:
                        off = placed[best.path]["offset"] + off_f - cut / FINE_HZ
                else:
                    probe = p_env[: max(FINE_HZ * 2, min(len(p_env), len(a_env) - int(lo * FINE_HZ)))]
                    off_f, conf_f = correlate(a_env, probe, FINE_HZ, (max(0, lo), hi))
                    if off_f is not None and conf_f > 1:
                        off = placed[best.path]["offset"] + off_f
            placed[c.path] = {"offset": round(float(off), 4), "conf": round(conf, 1), "how": "audio"}
        else:
            # only fall back to the clip's own clock when the editor said that camera's clock is right
            guess = (times[c.path] - t0) if (times[c.path] is not None and c.camera in trusted) else None
            placed[c.path] = {"offset": round(guess, 3) if guess is not None else None, "conf": round(conf, 1), "how": "timestamp" if guess is not None else "unsynced"}
        if i % 10 == 0 or i == len(others):
            log(f"sync {i}/{len(others)}")
    clock = _clock_correct(others, placed, times, t0, master, cover, envs)
    return {"anchor": anchor_camera, "t0": t0, "clips": placed, "clock": clock}


CLOCK_TOL_S = 60.0     # verified matches within this of the camera's clock error agree with each other
CLOCK_MIN_N = 5        # ...and at least this many must agree before the camera's clock is trusted
CLOCK_MIN_SHARE = 0.4  # ...and they must be at least this share of the camera's audio matches
CLOCK_REFINE_S = 15.0  # clock placements are refined by sound inside this window


def _clock_correct(others, placed, times, t0, master, cover, envs):
    """Per camera: learn its clock error from verified sound matches. If they agree, the clock is wrong
    by a constant: drop sound matches that disagree with it, place every other clip by its corrected
    clock, and refine each placement by sound inside a small window. Cameras whose matches don't agree
    keep only their verified matches; nothing is placed by their clock."""
    report = {}
    for cam in sorted({c.camera for c in others}):
        cc = [c for c in others if c.camera == cam]
        # timestamps more than 2 days from the anchor day are a reset clock (e.g. 2018-01-01): not usable
        ok_t = {c.path for c in cc if times[c.path] is not None and abs(times[c.path] - t0) < 2 * 86400}
        errs = sorted(placed[c.path]["offset"] - (times[c.path] - t0) for c in cc
                      if placed[c.path]["how"] == "audio" and c.path in ok_t)
        n_audio = sum(1 for c in cc if placed[c.path]["how"] == "audio")
        best, err = [], None
        for e in errs:
            grp = [x for x in errs if abs(x - e) <= CLOCK_TOL_S]
            if len(grp) > len(best):
                best = grp
        if best:
            err = float(np.median(best))
        if not best or len(best) < CLOCK_MIN_N or len(best) < CLOCK_MIN_SHARE * max(1, n_audio):
            report[cam] = {"clock_error_s": None, "agreeing": len(best), "audio_matches": n_audio,
                           "note": "clock not consistent: only verified sound matches kept"}
            log(f"clock {cam}: not consistent ({len(best)}/{n_audio} matches agree) - verified sound matches only")
            continue
        dropped = placed_n = refined = 0
        for c in cc:
            v = placed[c.path]
            if c.path not in ok_t:
                continue  # reset clock on this clip: keep a verified sound match if it has one, else unsynced
            guess = times[c.path] - t0 + err
            if v["how"] == "audio" and abs(v["offset"] - guess) <= CLOCK_TOL_S:
                continue  # sound and clock agree
            if v["how"] == "audio":
                dropped += 1
            # refine by sound near the corrected clock
            e = envs.get(c.path)
            new = {"offset": round(guess, 3), "conf": 0.0, "how": "clock"}
            if e is not None and len(e):
                o, _ = correlate(master, e, ENV_HZ, (guess - CLOCK_REFINE_S, guess + CLOCK_REFINE_S))
                if o is not None:
                    r = _verify(master, cover, e, int(round(o * ENV_HZ)), ENV_HZ)
                    if r >= MIN_R:
                        new = {"offset": round(float(o), 4), "conf": round(r * 100, 1), "how": "audio"}
                        refined += 1
            placed[c.path] = new
            placed_n += 1
        report[cam] = {"clock_error_s": round(err, 2), "agreeing": len(best), "audio_matches": n_audio,
                       "dropped_false_matches": dropped, "placed_by_clock": placed_n - refined, "refined_by_sound": refined}
        log(f"clock {cam}: off by {err:+.1f}s ({len(best)}/{n_audio} matches agree); dropped {dropped} false matches; "
            f"{placed_n - refined} placed by clock, {refined} refined by sound")
    return report


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("clips_json")
    ap.add_argument("out_json")
    ap.add_argument("--anchor")
    ap.add_argument("--trusted", nargs="*")
    ap.add_argument("--exclude", nargs="*")
    a = ap.parse_args()
    clips = [Clip.from_json(d) for d in load_json(a.clips_json)]
    res = sync(clips, a.anchor, a.trusted, set(a.exclude or []))
    save_json(a.out_json, res)
    n = sum(1 for v in res["clips"].values() if v["how"] == "audio")
    log(f"synced by audio: {n}; anchor: {sum(1 for v in res['clips'].values() if v['how']=='anchor')}; fallback: {sum(1 for v in res['clips'].values() if v['how'] in ('timestamp','unsynced'))}")
