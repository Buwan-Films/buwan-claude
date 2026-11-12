"""Transcribe on arrival: every camera clip that has someone talking gets a transcript, so the story work
(/buwan:plot) starts from text instead of from listening.

Local, nothing leaves the computer: whisper.cpp (`whisper-cli`, Homebrew `whisper-cpp`) with the
large-v3-turbo model and the Silero voice detector (~/.buwan/models, installed by /buwan:setup-kit).
About 35x real time on Apple Silicon: a 12-minute ceremony clip in ~20 s.

Which clips: camera clips with sound, at least MIN_SECONDS long, not rejected by the cull, not aerial,
and loud enough to hold speech (the cull's loudness reading). Clips already transcribed are skipped,
so it can run after every /buwan:sync.

Per clip:  edit/transcripts/<camera>/<card>/<clip>.srt and .txt (clip time, verbatim - Taglish kept as spoken)
Index:     edit/assemble/transcripts.json  {raw path: {speech, words, spoken_s, language, hint, text, srt}}
Report:    edit/transcripts_report.md      the speech clips: clip, camera, length, words, what it sounds like, first line

`hint` is a guess from the words (vows, mass, speech/toast, interview/message, talk); the editor and
/buwan:plot decide what it is. Never written into the raw folder.
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from common import Clip, load_json, log, save_json

MODELS = Path(os.environ.get("BUWAN_MODELS", Path.home() / ".buwan" / "models"))
MODEL = Path(os.environ.get("BUWAN_WHISPER_MODEL", MODELS / "ggml-large-v3-turbo.bin"))
VAD = MODELS / "ggml-silero-v5.1.2.bin"
MIN_SECONDS = 20          # shorter clips are b-roll moments, not speech
MIN_LUFS = -48            # quieter than this: no usable speech on the camera mic
AERIAL = ("drone", "dji", "aerial", "mavic")
MIN_WORDS = 25            # a clip "has speech" from this many words ...
MIN_SPOKEN = 12.0         # ... spoken over at least this many seconds
BATCH = 12                # clips per whisper run (the model loads once per run)

HINTS = {
    "vows": ["i take you", "take you to be", "to have and to hold", "in sickness and in health", "for better", "i vow",
             "i promise to", "my vow", "tinatanggap kita", "ipinapangako", "pangako ko", "mangangako", "habang buhay"],
    "mass": ["the lord be with you", "let us pray", "body of christ", "lamb of god", "lift up your hearts", "holy spirit",
             "peace be with you", "panginoon", "manalangin tayo", "sumainyo", "ama namin", "amen"],
    "speech/toast": ["cheers", "toast", "raise your glass", "congratulations", "to the newlyweds", "to the bride and groom",
                     "good evening everyone", "thank you all for coming", "maraming salamat", "mabuhay ang bagong kasal", "mabuhay"],
    "interview/message": ["i love you", "mahal kita", "mahal na mahal", "when i first", "first time i saw", "nung una",
                          "message", "dear", "sana", "ingat", "happy for you"],
}
JUNK = re.compile(r"^[\s\W_]*$|^\s*[\[(].*[\])]\s*$|♪|\b(subtitles? by|thanks for watching|subscribe|amara\.org)\b", re.I)
JUNK_LINES = {"thank you.", "thank you", "you", "bye.", "bye", "okay.", "the end.", "."}


def available() -> str | None:
    """None when transcription can run, else the reason it can't."""
    if not (shutil.which("whisper-cli") or Path("/opt/homebrew/bin/whisper-cli").exists()):
        return "whisper-cli not installed (brew install whisper-cpp, or /buwan:setup-kit)"
    if not MODEL.exists():
        return f"whisper model missing: {MODEL} (/buwan:setup-kit downloads it)"
    return None


def _whisper() -> str:
    return shutil.which("whisper-cli") or "/opt/homebrew/bin/whisper-cli"


def candidates(clips: dict[str, Clip], cull: dict[str, dict], done: dict, only: set[str] | None = None) -> tuple[list[Clip], dict]:
    todo, skipped = [], {}
    for p, c in clips.items():
        if only is not None and p not in only:
            continue
        if p in done:
            continue
        why = None
        if c.camera == "music" or c.kind != "video":
            why = "not a camera clip"
        elif not c.has_audio:
            why = "no sound"
        elif any(k in (c.camera or "").lower() for k in AERIAL):
            why = "aerial"
        elif c.duration < MIN_SECONDS:
            why = f"shorter than {MIN_SECONDS} s"
        else:
            cu = cull.get(p) or {}
            if cu.get("reject"):
                why = "left out by the cull"
            elif (cu.get("metrics") or {}).get("lufs") is not None and cu["metrics"]["lufs"] < MIN_LUFS:
                why = f"too quiet for speech ({cu['metrics']['lufs']:.0f} LUFS)"
        if why:
            skipped[p] = why
        else:
            todo.append(c)
    todo.sort(key=lambda c: -c.duration)   # the long ones (ceremony, speeches) first
    return todo, skipped


def _clean_segments(segs: list[dict]) -> list[dict]:
    out, last, rep = [], None, 0
    for s in segs:
        t = re.sub(r"\s+", " ", s.get("text", "")).strip()
        if not t or JUNK.search(t) or t.lower() in JUNK_LINES:
            continue
        if last and t.lower() == last.lower():
            rep += 1
            if rep >= 2:          # whisper looping on music/noise
                continue
        else:
            rep = 0
        last = t
        out.append({"start": s["offsets"]["from"] / 1000.0, "end": s["offsets"]["to"] / 1000.0, "text": t})
    return out


def _srt_time(sec: float) -> str:
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _hint(text: str) -> str:
    low = " " + text.lower() + " "
    score = {k: sum(low.count(w) for w in words) for k, words in HINTS.items()}
    k = max(score, key=score.get)
    return k if score[k] >= 2 else "talk"


def _rel(c: Clip) -> Path:
    return Path(c.rel) if c.rel else Path(c.camera or "clips") / Path(c.path).name


def _extract(c: Clip, wav: Path) -> bool:
    r = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", "-i", c.path, "-vn", "-ac", "1", "-ar", "16000",
                        "-c:a", "pcm_s16le", str(wav)], capture_output=True)
    return r.returncode == 0 and wav.exists() and wav.stat().st_size > 1000


def transcribe(project: Path, clips: dict[str, Clip], only: set[str] | None = None, language: str = "auto",
               redo: bool = False, limit: int = 0, threads: int = 8) -> dict:
    ad = project / "edit" / "assemble"
    idx_path = ad / "transcripts.json"
    index = {} if redo or not idx_path.exists() else load_json(idx_path)
    why = available()
    if why:
        log(f"transcribe: skipped - {why}")
        return index
    cull = {d["path"]: d for d in load_json(ad / "cull.json")} if (ad / "cull.json").exists() else {}
    done = {p for p, v in index.items() if "speech" in v}
    todo, skipped = candidates(clips, cull, done, only)
    if limit:
        todo = todo[:limit]
    for p, w in skipped.items():
        index.setdefault(p, {"skipped": w})
    total = sum(c.duration for c in todo)
    log(f"transcribe: {len(todo)} clips ({total / 60:.0f} min of sound) with whisper large-v3-turbo, language {language}"
        + (f"; {len(done)} already transcribed" if done else ""))
    if not todo:
        save_json(idx_path, index)
        return index
    tdir = project / "edit" / "transcripts"
    tmp = tdir / ".work"
    tmp.mkdir(parents=True, exist_ok=True)
    vad = ["--vad", "-vm", str(VAD)] if VAD.exists() else []
    t0, n_done = time.time(), 0
    for b in range(0, len(todo), BATCH):
        batch = todo[b:b + BATCH]
        wavs = {c.path: tmp / f"{b + i:05d}.wav" for i, c in enumerate(batch)}
        with cf.ThreadPoolExecutor(4) as ex:
            ok = dict(zip(wavs, ex.map(lambda p: _extract(clips[p], wavs[p]), wavs)))
        files = [str(wavs[p]) for p in wavs if ok[p]]
        if files:
            cmd = [_whisper(), "-m", str(MODEL), *vad, "-l", language, "-t", str(threads), "-oj", "-np"]
            for f in files:
                cmd += ["-f", f]
            subprocess.run(cmd, capture_output=True, timeout=max(600, int(sum(clips[p].duration for p in wavs) * 2)))
        for c in batch:
            wav = wavs[c.path]
            js = Path(str(wav) + ".json")
            if not ok[c.path] or not js.exists():
                index[c.path] = {"skipped": "could not read the sound" if not ok[c.path] else "whisper failed"}
            else:
                d = json.loads(js.read_text(encoding="utf-8", errors="replace"))
                segs = _clean_segments(d.get("transcription", []))
                text = " ".join(s["text"] for s in segs)
                words = len(text.split())
                spoken = sum(s["end"] - s["start"] for s in segs)
                rel = _rel(c)
                srt = tdir / rel.with_suffix(".srt")
                srt.parent.mkdir(parents=True, exist_ok=True)
                srt.write_text("".join(f"{i}\n{_srt_time(s['start'])} --> {_srt_time(s['end'])}\n{s['text']}\n\n"
                                       for i, s in enumerate(segs, 1)), encoding="utf-8")
                srt.with_suffix(".txt").write_text(text + "\n", encoding="utf-8")
                speech = words >= MIN_WORDS and spoken >= MIN_SPOKEN
                index[c.path] = {"speech": speech, "words": words, "spoken_s": round(spoken, 1), "duration": round(c.duration, 1),
                                 "camera": c.camera, "language": (d.get("result") or {}).get("language"),
                                 "hint": _hint(text) if speech else None, "text": text[:400], "srt": str(srt)}
            for f in (wav, Path(str(wav) + ".json")):
                f.unlink(missing_ok=True)
        n_done += len(batch)
        save_json(idx_path, index)   # resume-safe
        el = time.time() - t0
        left = sum(c.duration for c in todo[b + BATCH:])
        rate = sum(c.duration for c in todo[:b + BATCH]) / max(el, 1)
        log(f"transcribe: {n_done}/{len(todo)} clips, {sum(1 for c in todo[:n_done] if index[c.path].get('speech'))} with speech"
            + (f", ~{left / rate / 60:.0f} min left" if left else ""))
    shutil.rmtree(tmp, ignore_errors=True)
    write_report(project, index)
    return index


def write_report(project: Path, index: dict) -> Path:
    rows = sorted(((p, v) for p, v in index.items() if v.get("speech")), key=lambda x: (x[1].get("camera") or "", Path(x[0]).name))
    lines = ["# Transcripts", "",
             f"{len(rows)} clips with speech, transcribed on this computer (whisper large-v3-turbo). "
             "Verbatim as heard - check names and Taglish words before captions. Full text: `edit/transcripts/`.", "",
             "| Clip | Camera | Length | Words | Sounds like | First words |", "|---|---|---|---|---|---|"]
    for p, v in rows:
        d = v.get("duration") or 0
        first = (v.get("text") or "")[:90].replace("|", "/")
        lines.append(f"| {Path(p).name} | {v.get('camera', '')} | {int(d // 60)}:{int(d % 60):02d} | {v['words']} | {v.get('hint')} | {first}… |")
    out = project / "edit" / "transcripts_report.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"transcribe: {len(rows)} clips with speech -> {out}")
    return out
