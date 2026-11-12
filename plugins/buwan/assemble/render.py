"""Render: new enhanced clips from the raw footage, into a new folder on every run. The raw files are only read.

Per clip (read from the raw folder, same relative path; written as <out>/<camera>/<card>/<clip>.mov):
  clip with a fix    exposure and/or white balance fix (exposure.json) -> HEVC 10-bit. No grade: the look is applied in the
                     editing app (/buwan:grade). `--look <.cube>` bakes a look in, only when asked.
  clip with no fix   copied as it is (the original file, same name and extension; an APFS clone when the folder is on the
                     same drive, so it takes no time and no extra space) -> the folder holds every clip of the day and the
                     editor imports one folder. Re-encoding an unchanged clip would only add a generation of compression.
                     `--reencode-all` renders them to HEVC 10-bit instead (e.g. for smooth playback of 4:2:2 H.264).
  shaky Creative/Glider clips (steady.json: best-cut / warp) trimmed to the best cut, then a smooth glide with
                     vid.stab (two passes; needs the Buwan ffmpeg with libvidstab: ~/.buwan/ffmpeg-vidstab)
  everything else    the original audio, untouched (interviews and vows too: their angles, best audio and dead air
                     are made by `assemble.js speech` into <raw>_SPEECH_<date-time>/)
Resumable: a clip whose output already exists is skipped (pass --out to continue a run; --redo re-renders it in place,
e.g. `--only fixed --redo --out <folder>` after white balance / the superwhite fix were added to an earlier run). Log: <out>/render_log.csv.
"""
from __future__ import annotations

import concurrent.futures as cf
import csv
import datetime as _dt
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from common import Clip, log

BUWAN_FFMPEG = Path.home() / ".buwan" / "ffmpeg-vidstab" / "bin" / "ffmpeg"
CREATIVE = ("creative", "glider", "gimbal", "ronin", "steadi")
VIDEO_BITRATE = "80M"
FADE = 0.02
TARGET_LUFS = -17.0
TARGET_TP = -6.0


def ffmpeg_bin() -> str:
    return str(BUWAN_FFMPEG) if BUWAN_FFMPEG.exists() else (shutil.which("ffmpeg") or "ffmpeg")


def has_vidstab(ff: str) -> bool:
    r = subprocess.run([ff, "-hide_banner", "-filters"], capture_output=True, text=True)
    return "vidstabtransform" in r.stdout


def _esc(p: str) -> str:
    return p.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


HEADROOM = 876 / (1019 - 64)   # 10-bit: white 940, the camera's superwhite top 1019, black 64


def _squeeze(k: float) -> str:
    return f"lutyuv=y='64+(val-64)*{k:.6f}':u='512+(val-512)*{k:.6f}':v='512+(val-512)*{k:.6f}'"


def _grade_chain(ev: float, cube: str | None, wb: list[float] | None = None) -> str:
    wb = wb or [1.0, 1.0, 1.0]
    if not cube:
        # exposure + white balance (the default): one 16-bit per-channel RGB gain, same result as the float filters, ~1.5x faster
        gains = [(2.0 ** ev) * k for k in wb]
        if all(abs(x - 1.0) < 1e-4 for x in gains):
            return "format=p010le"
        # Keep the superwhites (camera video levels above white, up to code 1019) so the grade can still pull them back:
        # the RGB step clips at white, so the levels are first squeezed under it in YUV (a uniform YUV scale about black
        # is exactly a uniform RGB gain), the per-channel gains applied in 16-bit RGB, then the squeeze undone.
        lv = ":".join(f"{c}imax={1 / x:.5f}" if x >= 1 else f"{c}omax={x:.5f}" for c, x in zip("rgb", gains))
        return f"format=yuv420p10le,{_squeeze(HEADROOM)},format=rgb48le,colorlevels={lv},format=yuv420p10le,{_squeeze(1 / HEADROOM)},format=p010le"
    # baking a look in (only when render --look is passed; normally the grade is applied in the editing app: /buwan:grade)
    parts = ["format=gbrpf32le"]
    if wb != [1.0, 1.0, 1.0]:
        parts.append(f"colorchannelmixer=rr={wb[0]:.4f}:gg={wb[1]:.4f}:bb={wb[2]:.4f}")
    if ev:
        parts.append(f"exposure=exposure={ev:.3f}")
    if cube:
        parts.append(f"lut3d=file='{_esc(cube)}':interp=tetrahedral")
    parts.append("format=p010le")
    return ",".join(parts)


def _encode_args(out: Path) -> list[str]:
    return ["-c:v", "hevc_videotoolbox", "-profile:v", "main10", "-b:v", VIDEO_BITRATE, "-tag:v", "hvc1",
            "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
            "-movflags", "+faststart", str(out)]


def _run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "").strip()[-400:])


def render_clip(ff: str, src: Path, out: Path, job: dict, cube: str | None, vidstab: bool) -> str:
    tmp = out.with_name(out.stem + ".part.mov")
    grade = _grade_chain(job["ev"], cube, job.get("wb"))
    what = []
    if job.get("ranges") is not None and job["ranges"]:
        # speech: cut to the speech ranges, cleaned audio, fades at the joins
        rs = job["ranges"]
        inputs = ["-i", str(src)] + (["-i", job["clean"]] if job.get("clean") else [])
        aidx = 1 if job.get("clean") else 0
        fc = []
        for i, (a, b) in enumerate(rs):
            d = b - a
            fc.append(f"[0:v]trim=start={a:.3f}:end={b:.3f},setpts=PTS-STARTPTS[v{i}]")
            fo = max(0.0, d - FADE)
            fc.append(f"[{aidx}:a]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS,afade=t=in:d={FADE},afade=t=out:st={fo:.3f}:d={FADE}[a{i}]")
        fc.append("".join(f"[v{i}][a{i}]" for i in range(len(rs))) + f"concat=n={len(rs)}:v=1:a=1[vc][acat]")
        # level the speech that is left (dead air gone) to the house target: -17 LUFS, peaks at -6 dBFS
        # loudnorm aims 1 LU hot into the -6 dB limiter: clipped or peaky sources otherwise land 2 LU short of the target
        fc.append(f"[acat]loudnorm=I={TARGET_LUFS + 1:.1f}:TP=-1.5:LRA=11,alimiter=limit={TARGET_TP}dB:level=disabled,aresample=48000[ac]")
        fc.append(f"[vc]{grade}[vo]")
        cmd = [ff, "-v", "error", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", "[vo]", "-map", "[ac]",
               "-c:a", "aac", "-b:a", "320k", "-ar", "48000"] + _encode_args(tmp)
        _run(cmd)
        what.append(f"speech: {len(rs)} ranges, dead air out" + (", clean audio" if job.get("clean") else "") + ", -17 LUFS")
    elif job.get("trim"):
        a, b = job["trim"]
        if vidstab:
            trf = Path(tempfile.gettempdir()) / f"buwan_{os.getpid()}_{abs(hash(str(src))) % 10**8}.trf"
            _run([ff, "-v", "error", "-y", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", str(src), "-vf",
                  f"vidstabdetect=shakiness=7:accuracy=15:result='{_esc(str(trf))}'", "-f", "null", "-"])
            vf = (f"vidstabtransform=input='{_esc(str(trf))}':smoothing=25:optzoom=1:zoomspeed=0.2:interpol=bicubic,"
                  f"unsharp=5:5:0.5:3:3:0.0,{grade}")
            what.append(f"best cut {a:.1f}-{b:.1f}s, smooth glide (vid.stab)")
        else:
            trf, vf = None, grade
            what.append(f"best cut {a:.1f}-{b:.1f}s (no vid.stab in this ffmpeg: not stabilized)")
        _run([ff, "-v", "error", "-y", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", str(src), "-vf", vf,
              "-map", "0:v:0", "-map", "0:a?", "-c:a", "aac", "-b:a", "320k"] + _encode_args(tmp))
        if trf:
            Path(trf).unlink(missing_ok=True)
    else:
        _run([ff, "-v", "error", "-y", "-i", str(src), "-vf", grade, "-map", "0:v:0", "-map", "0:a?", "-c:a", "copy"] + _encode_args(tmp))
        if job.get("flag"):
            what.append(job["flag"])
    tmp.rename(out)
    if job["ev"]:
        what.append(f"exposure {job['ev']:+.2f} EV")
    if job.get("wb"):
        what.append("white balance R {:.3f} G {:.3f} B {:.3f}".format(*job["wb"]))
    if cube:
        what.append("look baked in")
    return "; ".join(what)


def needs_render(job: dict, cube: str | None) -> bool:
    return bool(cube or job.get("ev") or job.get("wb") or job.get("trim") or job.get("ranges"))


def copy_clip(src: Path, dst: Path) -> str:
    """The original, unchanged: an APFS clone (instant, no extra space) when possible, else a byte copy; size checked."""
    tmp = dst.with_name(dst.stem + ".part" + dst.suffix)
    tmp.unlink(missing_ok=True)
    cloned = False
    if sys.platform == "darwin":
        cloned = subprocess.run(["cp", "-c", str(src), str(tmp)], capture_output=True).returncode == 0
    if not cloned:
        tmp.unlink(missing_ok=True)
        shutil.copy2(src, tmp)
    if tmp.stat().st_size != src.stat().st_size:
        tmp.unlink(missing_ok=True)
        raise RuntimeError("copy size mismatch")
    tmp.rename(dst)
    return "original copied, no fix needed" + (" (clone)" if cloned else "")


def plan_jobs(project: Path, clips: dict[str, Clip], categories: dict) -> dict[str, dict]:
    adir = project / "edit" / "assemble"
    load = lambda n: json.loads((adir / n).read_text()) if (adir / n).exists() else {}
    expo, steady = load("exposure.json"), load("steady.json")
    cull = {m["path"]: m for m in (json.loads((adir / "cull.json").read_text()) if (adir / "cull.json").exists() else [])}
    jobs = {}
    for p, c in clips.items():
        if c.kind != "video" or c.camera == "music":
            continue
        if (cull.get(p) or {}).get("reject"):
            continue
        e = expo.get(p) or {}
        j = {"ev": e.get("ev") or 0.0, "wb": e.get("wb")}
        if j["ev"] > 0 and j["wb"] and e.get("yhigh"):   # brighter + a channel gain above 1: keep the 90th percentile under the cap
            import math
            j["ev"] = round(max(0.0, min(j["ev"], math.log2(225.0 / (e["yhigh"] * max(j["wb"]))))), 2)
        # interviews, letters, speeches and vows go through like any clip (exposure, original audio, full length);
        # merging their angles, the best audio and dead air are the speech skill's job (assemble.js speech)
        st = steady.get(p) or {}
        if st.get("decision") in ("best-cut", "warp") and st.get("range") and \
                any(k in (c.camera or "").lower() for k in CREATIVE):
            j["trim"] = st["range"]
        jobs[p] = j
    return jobs


def run(project: Path, clips: dict[str, Clip], categories: dict, raw_copy: Path, source: Path, out: Path | None,
        cube: str | None, workers: int = 3, limit: int = 0, only: str | None = None, redo: bool = False,
        reencode_all: bool = False) -> dict:
    ff = ffmpeg_bin()
    vidstab = has_vidstab(ff)
    out = out or source.parent / f"{source.name}_ENHANCED_{_dt.datetime.now():%Y%m%d-%H%M}"
    out.mkdir(parents=True, exist_ok=True)
    jobs = plan_jobs(project, clips, categories)
    items = []
    for p, j in jobs.items():
        rel = Path(os.path.relpath(p, raw_copy))
        src = source / rel
        if not src.exists():
            src = Path(p)   # fall back to the working copy (same bytes) if the raw folder moved
        kind = "shaky" if "trim" in j else "clip"
        if not reencode_all and not needs_render(j, cube):
            kind = "copy"
        if only == "wb":
            if not j.get("wb"):
                continue
        elif only == "fixed":   # every clip with a fix (exposure, white balance, shaky best cut); nothing copied
            if kind == "copy":
                continue
        elif only == "copy":    # only the clips with no fix, copied as they are
            if kind != "copy":
                continue
        elif only and kind != only:
            continue
        dst = out / rel if kind == "copy" else out / rel.with_suffix(".mov")
        items.append((p, src, dst, j, kind))
    items.sort(key=lambda x: ({"shaky": 0, "clip": 1}.get(x[4], 2), str(x[2])))   # shaky first (the ones to check), copies last
    if limit:
        items = items[:limit]
    n_copy = sum(1 for it in items if it[4] == "copy")
    log(f"render: {len(items) - n_copy} clips to render + {n_copy} with no fix to copy as they are -> {out} (ffmpeg {'with' if vidstab else 'WITHOUT'} vid.stab, look {Path(cube).name if cube else 'none'})")
    rows, done = [], 0

    def one(it):
        p, src, dst, j, kind = it
        if dst.exists() and dst.stat().st_size > 0 and not redo:
            return [str(src), str(dst), kind, "already there"]
        if kind == "copy" and dst.with_suffix(".mov") != dst and dst.with_suffix(".mov").exists():
            return [str(src), str(dst.with_suffix(".mov")), kind, "already rendered by an earlier run"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            if kind == "copy":
                return [str(src), str(dst), kind, copy_clip(src, dst)]
            return [str(src), str(dst), kind, render_clip(ff, src, dst, j, cube, vidstab)]
        except Exception as e:
            dst.with_name(dst.stem + ".part" + dst.suffix).unlink(missing_ok=True)
            return [str(src), str(dst), kind, f"FAILED: {e}"]

    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for r in ex.map(one, items):
            rows.append(r)
            done += 1
            if done % 10 == 0 or done == len(items):
                log(f"render {done}/{len(items)}")
    new = not (out / "render_log.csv").exists()
    with open(out / "render_log.csv", "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["source", "enhanced", "kind", "what was done"])
        w.writerows(rows)
    failed = [r for r in rows if r[3].startswith("FAILED")]
    log(f"render: {len(rows) - len(failed)} done, {len(failed)} failed -> {out}")
    for r in failed[:10]:
        log(f"  FAILED {r[0]}: {r[3][:200]}")
    return {"out": str(out), "clips": len(rows), "failed": len(failed)}
