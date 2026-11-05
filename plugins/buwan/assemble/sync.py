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
MIN_CONF = 6.0       # peak / median ratio to accept a match


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
    peak = c[k]
    med = np.median(np.abs(c)) + 1e-9
    conf = float(peak / med)
    return k / hz, conf


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
    envs = {}
    for c in anchor:
        e = envelope(c.path)
        envs[c.path] = e
        k = int(placed[c.path]["offset"] * ENV_HZ)
        master[k:k + len(e)] += e[: len(master) - k]
    others = [c for c in vids if c.camera != anchor_camera]
    for i, c in enumerate(others, 1):
        e = envelope(c.path)
        envs[c.path] = e
        search = None
        if c.camera in trusted and times[c.path] is not None:
            guess = times[c.path] - t0
            search = (guess - 120, guess + 120)
        off, conf = correlate(master, e, ENV_HZ, search)
        if off is None or conf < MIN_CONF:
            # second try without the window
            if search:
                off2, conf2 = correlate(master, e, ENV_HZ, None)
                if conf2 > conf:
                    off, conf = off2, conf2
        if off is not None and conf >= MIN_CONF:
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
                    if off_f is not None and conf_f > 3:
                        off = placed[best.path]["offset"] + off_f - cut / FINE_HZ
                else:
                    probe = p_env[: max(FINE_HZ * 2, min(len(p_env), len(a_env) - int(lo * FINE_HZ)))]
                    off_f, conf_f = correlate(a_env, probe, FINE_HZ, (max(0, lo), hi))
                    if off_f is not None and conf_f > 3:
                        off = placed[best.path]["offset"] + off_f
            placed[c.path] = {"offset": round(float(off), 4), "conf": round(conf, 1), "how": "audio"}
        else:
            guess = (times[c.path] - t0) if times[c.path] is not None else None
            placed[c.path] = {"offset": round(guess, 3) if guess is not None else None, "conf": round(conf, 1), "how": "timestamp" if guess is not None else "unsynced"}
        if i % 10 == 0 or i == len(others):
            log(f"sync {i}/{len(others)}")
    return {"anchor": anchor_camera, "t0": t0, "clips": placed}


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
