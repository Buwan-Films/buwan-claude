"""Synthetic end-to-end test for the assemble engine.

Builds a fake wedding (3 cameras + drone sharing one event sound, one camera with no clock, a false start, a black
clip), two music tracks with known tempo and a louder peak section, categories and Story-Lock selects, then runs
scan -> cull -> music -> sync -> organize -> selects -> build and checks the results. The FCPXML files it writes
can be imported into Final Cut Pro to confirm the builder on a real machine.
"""
from __future__ import annotations

import json
import subprocess
import sys
import xml.dom.minidom
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from common import log, save_json  # noqa: E402

SR = 48000


def _wav(path, y):
    import soundfile as sf
    sf.write(str(path), np.clip(y, -1, 1).astype(np.float32), SR)


def event_audio(seconds, seed=7):
    rng = np.random.default_rng(seed)
    n = seconds * SR
    y = rng.normal(0, 0.01, n)
    # claps/impulses at irregular times + a "speech-like" amplitude-modulated tone region
    for t in np.sort(rng.uniform(0, seconds, int(seconds * 1.5))):
        i = int(t * SR)
        L = int(0.08 * SR)
        y[i:i + L] += (rng.normal(0, 1, min(L, n - i)) * np.exp(-np.linspace(0, 6, min(L, n - i)))) * 0.5
    t = np.arange(n) / SR
    # speech-like: random syllable bursts of a few harmonics with random pitch and length
    pos = 0.0
    while pos < seconds - 0.5:
        L = rng.uniform(0.08, 0.35)
        f0 = rng.uniform(110, 260)
        i, m = int(pos * SR), int(L * SR)
        tt = np.arange(m) / SR
        syl = sum(np.sin(2 * np.pi * f0 * h * tt) / h for h in (1, 2, 3)) * np.hanning(m) * 0.15
        y[i:i + m] += syl[: n - i]
        pos += L + rng.uniform(0.02, 0.5 if rng.random() < 0.15 else 0.12)
    y[int(seconds * 0.55 * SR):int(seconds * 0.62 * SR)] *= 0.1  # a quiet stretch
    return y


def music(seconds, bpm, peak=(None, None), seed=1):
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    y = np.zeros(n)
    beat = 60 / bpm
    k = 0
    while k * beat < seconds:
        i = int(k * beat * SR)
        L = int(0.12 * SR)
        env = np.exp(-np.linspace(0, 8, L))
        kick = np.sin(2 * np.pi * np.linspace(90, 40, L) * np.linspace(0, 0.12, L)) * env
        amp = 1.0 if k % 4 == 0 else 0.55
        y[i:i + L] += kick[: n - i] * amp
        if k % 2 == 1:
            hat = rng.normal(0, 1, L) * np.exp(-np.linspace(0, 20, L)) * 0.15
            y[i:i + L] += hat[: n - i]
        k += 1
    # pad that rises then falls; louder in the peak window
    gain = 0.15 + 0.35 * np.clip(t / (seconds * 0.6), 0, 1)
    if peak[0] is not None:
        gain += 0.6 * ((t >= peak[0]) & (t < peak[1]))
    tail = np.clip((seconds - t) / 15, 0, 1)
    pad = 0.3 * (np.sin(2 * np.pi * 110 * t) + 0.5 * np.sin(2 * np.pi * 165 * t))
    y = (y + pad) * gain * tail
    return y * 0.8 / max(1e-6, np.abs(y).max())


def render_clip(out, wav, start, dur, size, rate, created=None, pattern="testsrc2", extra_vf=None):
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"{pattern}=size={size}:rate={rate}", "-ss", f"{start}", "-t", f"{dur}", "-i", str(wav),
           "-t", f"{dur}", "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k"]
    if extra_vf:
        cmd += ["-vf", extra_vf]
    if created:
        cmd += ["-metadata", f"creation_time={created}"]
    cmd += [str(out)]
    subprocess.run(cmd, check=True)


def run_selftest(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    foot = out / "Videos"
    proj = out / "projects" / "2026-01-01_Selftest_wedding"
    for d in (foot / "A-Main", foot / "B-Second", foot / "C-NoClock", foot / "D-Drone", out / "music", proj / "edit"):
        d.mkdir(parents=True, exist_ok=True)
    EVENT = 150
    log("selftest: synthesising event audio and music")
    ev = event_audio(EVENT)
    _wav(out / "event.wav", ev)
    _wav(out / "music" / "01_intro.wav", music(32, 100, seed=3))
    _wav(out / "music" / "02_story.wav", music(130, 120, peak=(70, 95), seed=4))
    # cameras: name -> list of (start, dur, size, rate, created?)  created = fake wall clock from 2026-01-01T10:00:00Z
    base = "2026-01-01T10:00:%02dZ"
    clips = {
        "A-Main": [(0, 60, "1920x1080", "24000/1001", True), (62, 60, "1920x1080", "24000/1001", True), (124, 26, "1920x1080", "24000/1001", True)],
        "B-Second": [(15, 50, "1920x1080", "30000/1001", True), (80, 55, "1920x1080", "30000/1001", True)],
        "C-NoClock": [(40, 45, "1280x720", "60000/1001", False), (100, 40, "1280x720", "60000/1001", False)],
        "D-Drone": [(30, 8, "3840x2160", "60000/1001", True)],
    }
    truth = {}
    patterns = {"A-Main": "testsrc2", "B-Second": "smptebars", "C-NoClock": "testsrc", "D-Drone": "mandelbrot"}
    log("selftest: rendering clips")
    for cam, lst in clips.items():
        for i, (st, du, size, rate, has_time) in enumerate(lst):
            name = f"{cam[0]}{i+1:04d}.mp4"
            created = None
            if has_time:
                created = f"2026-01-01T10:{st // 60:02d}:{st % 60:02d}.000000Z"
            render_clip(foot / cam / name, out / "event.wav", st, du, size, rate, created, patterns[cam])
            truth[str((foot / cam / name).resolve())] = st
    # false start + black clip
    render_clip(foot / "A-Main" / "A0099.mp4", out / "event.wav", 10, 0.3, "1920x1080", "24000/1001", None)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:size=1920x1080:rate=24000/1001", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                    "-t", "6", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(foot / "A-Main" / "A0098.mp4")], check=True)
    # categories + selects
    def P(cam, n):
        return str((foot / cam / n).resolve())
    cats = {P("A-Main", "A0001.mp4"): "01 Speech", P("A-Main", "A0002.mp4"): "01 Speech", P("A-Main", "A0003.mp4"): "07 Reception & Party",
            P("B-Second", "B0001.mp4"): "05 Reactions & BTS", P("B-Second", "B0002.mp4"): "04 Ceremony",
            P("C-NoClock", "C0001.mp4"): "03 Portraits", P("C-NoClock", "C0002.mp4"): "02 Prep & Details", P("D-Drone", "D0001.mp4"): "08 Drone",
            P("A-Main", "A0098.mp4"): "06 Establishing", P("A-Main", "A0099.mp4"): "06 Establishing"}
    save_json(proj / "edit" / "assemble" / "categories.json", cats)
    selects = [
        {"clip": P("A-Main", "A0001.mp4"), "in": 5.0, "out": 12.0, "beat": "welcome remarks", "part": "Storyline", "speaker": "Host", "text": "Welcome everyone"},
        {"clip": P("A-Main", "A0001.mp4"), "in": 20.0, "out": 29.0, "beat": "about the bride", "part": "Storyline", "speaker": "Maid of honor", "text": "She is matatag"},
        {"clip": P("A-Main", "A0001.mp4"), "in": 35.0, "out": 43.0, "beat": "about the groom", "part": "Storyline", "speaker": "Best man", "text": "He waited"},
        {"clip": P("A-Main", "A0002.mp4"), "in": 3.0, "out": 21.0, "beat": "vows", "part": "Ceremony", "speaker": "Groom", "text": "I promise"},
        {"clip": P("A-Main", "A0002.mp4"), "in": 25.0, "out": 31.0, "beat": "power statements", "part": "Ceremony", "speaker": "Officiant", "text": "You may kiss"},
        {"clip": P("A-Main", "A0002.mp4"), "in": 31.0, "out": 34.0, "beat": "kiss", "part": "Ceremony", "speaker": "", "text": "(kiss)"},
        {"clip": P("A-Main", "A0003.mp4"), "in": 2.0, "out": 9.0, "beat": "final wishes", "part": "Outro", "speaker": "Father", "text": "Hanggang sa pagtanda"},
    ]
    save_json(proj / "edit" / "assemble" / "selects.json", selects)
    (proj / "edit" / "SOURCES.md").write_text(f"Footage root (read-only): {foot.resolve()}\n")
    py = sys.executable
    A = str(Path(__file__).parent / "assemble.py")
    def run(*args):
        log("$ assemble " + " ".join(args))
        subprocess.run([py, A, *args], check=True)
    run("scan", str(proj), "--music", str(out / "music"))
    run("cull", str(proj), "--workers", "4")
    run("music", str(proj), "--intro", str(out / "music" / "01_intro.wav"), "--main", str(out / "music" / "02_story.wav"))
    run("sync", str(proj), "--anchor", "A-Main", "--trusted", "A-Main", "B-Second", "D-Drone")
    run("organize", str(proj), "--multicam", "--event", "Selftest")
    run("selects", str(proj), "--selects", str(proj / "edit" / "assemble" / "selects.json"), "--multicam", "--event", "Selftest")
    run("build", str(proj), "--selects", str(proj / "edit" / "assemble" / "selects.json"), "--multicam", "--event", "Selftest", "--name", "SDE Cut")
    # ---- checks ----
    ok = True
    cull = json.load(open(proj / "edit" / "assemble" / "cull.json"))
    rej = {Path(m["path"]).name: m["reject"] for m in cull if m["reject"]}
    log(f"CHECK cull: rejected {rej}")
    ok &= "A0099.mp4" in rej and "A0098.mp4" in rej and len(rej) == 2
    sync = json.load(open(proj / "edit" / "assemble" / "sync.json"))
    errs = []
    for p, v in sync["clips"].items():
        if p in truth and v["offset"] is not None:
            errs.append((Path(p).name, round(v["offset"] - truth[p], 3), v["how"], v["conf"]))
    log("CHECK sync (name, error s, how, conf): " + ", ".join(f"{n}:{e}({h},{c})" for n, e, h, c in errs))
    ok &= all(abs(e) <= 0.05 for _, e, h, _ in errs if h == "audio") and sum(1 for _, _, h, _ in errs if h == "audio") >= 4
    mus = json.load(open(proj / "edit" / "assemble" / "music.json"))
    log(f"CHECK music: intro {mus['intro']['tempo_bpm']} bpm (100), main {mus['main']['tempo_bpm']} bpm (120), peak {mus['main']['sections']['peak']} (70-95)")
    ok &= abs(mus["intro"]["tempo_bpm"] - 100) < 3 and abs(mus["main"]["tempo_bpm"] - 120) < 3 and abs(mus["main"]["sections"]["peak"][0] - 70) < 8
    for f in sorted((proj / "edit").glob("*.fcpxml")):
        xml.dom.minidom.parse(str(f))  # well-formed
        log(f"CHECK xml well-formed: {f.name} ({f.stat().st_size//1024} KB)")
    plan = json.load(open(next((proj / "edit").glob("sde-cut_v1.plan.json"))))
    log(f"CHECK build: {plan['stats']}  notes={plan['notes']}")
    ok &= plan["stats"]["broll_shots"] > 10
    log("SELFTEST " + ("PASS" if ok else "FAIL") + f"\nImport to verify in Final Cut: {proj / 'edit'}")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run_selftest(Path(sys.argv[1] if len(sys.argv) > 1 else "selftest")) else 1)
