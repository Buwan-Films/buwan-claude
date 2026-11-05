"""Music analysis for the music-driven cut.

For each track: tempo, beat times, bar (downbeat) times, an energy curve, and sections:
  intro-soft   quiet opening
  build        rising energy
  peak         the loudest sustained window  -> burst montage goes here
  release      after the peak
  outro        final decay -> resolution, logo reveal lands at the end
Two tracks are expected per film: track 1 = the intro (hook, no speech), track 2 = the story through the outro.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from common import log, save_json, run


def _load_mono_bytes(path, sr=22050):
    import subprocess
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True, check=True)
    return np.frombuffer(p.stdout, dtype=np.float32).copy(), sr


def analyse(path: str, role: str = "main") -> dict:
    import librosa
    y, sr = _load_mono_bytes(path)
    dur = len(y) / sr
    hop = 512
    onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    tempo, beat_frames = librosa.beat.beat_track(onset_envelope=onset, sr=sr, hop_length=hop, trim=False)
    tempo = float(np.atleast_1d(tempo)[0])
    beats = librosa.frames_to_time(beat_frames, sr=sr, hop_length=hop)
    # Octave correction: wedding edits cut on a 90-180 bpm feel. Halve/double as needed.
    if tempo and tempo < 88 and len(beats) > 2:
        mids = (beats[:-1] + beats[1:]) / 2
        beats = np.sort(np.concatenate([beats, mids]))
        beat_frames = librosa.time_to_frames(beats, sr=sr, hop_length=hop)
        tempo *= 2
    elif tempo > 185 and len(beats) > 4:
        beats = beats[::2]
        beat_frames = beat_frames[::2]
        tempo /= 2
    # Downbeats: pick the phase (0-3) whose beats carry the most onset energy, assuming 4/4.
    if len(beats) >= 8:
        strengths = onset[np.clip(beat_frames, 0, len(onset) - 1)]
        phase = int(np.argmax([strengths[p::4].mean() for p in range(4)]))
        bars = beats[phase::4]
    else:
        bars = beats[::4]
    # Energy curve at 10 Hz (RMS in dB, smoothed over ~2 s)
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop)[0]
    t_rms = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop)
    grid = np.arange(0, dur, 0.1)
    e = np.interp(grid, t_rms, rms)
    e_db = 20 * np.log10(np.maximum(e, 1e-5))
    k = 20
    e_s = np.convolve(e_db, np.ones(k) / k, mode="same")
    e_norm = (e_s - e_s.min()) / max(1e-6, (e_s.max() - e_s.min()))
    # Sections
    win = int(30 / 0.1)  # 30 s window
    if len(e_norm) > win:
        sums = np.convolve(e_norm, np.ones(win), mode="valid")
        p0 = int(np.argmax(sums)) * 0.1
    else:
        p0 = 0.0
    peak = [round(p0, 2), round(min(dur, p0 + 30), 2)]
    # soft intro: from 0 until energy first exceeds 0.45 (or 20 s max)
    above = np.where(e_norm > 0.45)[0]
    intro_end = round(min(float(above[0]) * 0.1 if len(above) else 20.0, max(8.0, dur * 0.25)), 2)
    intro_end = max(intro_end, round(min(8.0, dur * 0.2), 2))
    # outro: from the last time energy drops under 0.35 after the peak
    after = np.where((grid > peak[1]) & (e_norm < 0.35))[0]
    outro_start = round(float(after[0]) * 0.1, 2) if len(after) else round(max(peak[1], dur - 20), 2)
    sections = {
        "intro-soft": [0.0, intro_end],
        "build": [intro_end, peak[0]],
        "peak": peak,
        "release": [peak[1], outro_start],
        "outro": [outro_start, round(dur, 2)],
    }
    # Hits: strongest onsets (top 3%) -> good spots for title plate / logo
    thr = np.quantile(onset, 0.97) if len(onset) else 0
    hit_frames = np.where(onset >= thr)[0]
    hits = librosa.frames_to_time(hit_frames, sr=sr, hop_length=hop)
    # keep hits that sit on a beat (within 60 ms)
    hits_on_beat = [float(h) for h in hits if len(beats) and np.min(np.abs(beats - h)) < 0.06]
    return {
        "path": str(path), "role": role, "duration": round(dur, 3), "tempo_bpm": round(tempo, 2),
        "beats": [round(float(b), 3) for b in beats], "bars": [round(float(b), 3) for b in bars],
        "energy_10hz": [round(float(v), 3) for v in e_norm], "sections": sections,
        "hits": [round(h, 3) for h in hits_on_beat[:200]],
    }


def analyse_tracks(intro: str | None, main: str) -> dict:
    out = {"main": analyse(main, "main")}
    if intro:
        out["intro"] = analyse(intro, "intro")
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--intro")
    ap.add_argument("--main", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    res = analyse_tracks(a.intro, a.main)
    save_json(a.out, res)
    for k, v in res.items():
        log(f"{k}: {v['duration']:.1f}s  {v['tempo_bpm']} bpm  {len(v['beats'])} beats  sections={v['sections']}")
