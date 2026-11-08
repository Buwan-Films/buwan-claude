"""The working copy, organized by category: <WORK>/BY_CATEGORY/<category>[/<sub-bin>]/<camera>_<card>_<clip>.

Built from RAW_COPY after dedupe, cull, categories, sub-bins and steady:
  - every kept clip is cloned into its category folder (APFS clone = instant, no extra space;
    elsewhere a hard link, and a real copy only as the last resort);
  - cull rejects are left out (listed in logs/bycategory.csv);
  - flagged b-roll goes to 00 Flagged/<reason>, the same as the Premiere bins;
  - a shaky Creative/Glider clip with a best cut (steady pick, or the gimbal shot's best cut for Warp)
    is trimmed to that cut without re-encoding (`<name>_best_<in>-<out>.<ext>`); the full clip stays in RAW_COPY.

RAW_COPY and the originals are only read. BY_CATEGORY is footage too: protected like RAW_COPY.
edit/assemble/bycategory.json maps each RAW_COPY path to its category file, for the Premiere relink.
"""
from __future__ import annotations

import csv
import os
import shutil
import subprocess
import sys
from pathlib import Path

from common import Clip, load_json, log, save_json

OUT_DIR = "BY_CATEGORY"


def _clone(src: Path, dst: Path) -> str:
    if sys.platform == "darwin":
        r = subprocess.run(["cp", "-c", str(src), str(dst)], capture_output=True, text=True)
        if r.returncode == 0:
            return "clone"
    try:
        os.link(src, dst)
        return "hardlink"
    except OSError:
        shutil.copy2(src, dst)
        return "copy"


def _trim(src: Path, dst: Path, a: float, b: float) -> str:
    # stream copy: starts on the keyframe at or before `a`, so the cut can open a few frames early
    tmp = dst.with_name(dst.stem + ".part" + dst.suffix)
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", str(src),
                        "-map", "0:v:0", "-map", "0:a?", "-c", "copy", "-avoid_negative_ts", "make_zero",
                        "-movflags", "+faststart", str(tmp)], capture_output=True, text=True)
    if r.returncode != 0 or not tmp.exists() or tmp.stat().st_size == 0:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(r.stderr.strip()[-300:] or "ffmpeg failed")
    tmp.rename(dst)
    return "trim"


def _safe(name: str) -> str:
    return "".join(ch if ch not in '/\\:*?"<>|' else "-" for ch in name).strip()


def build(project: Path, clips: dict[str, Clip], categories: dict, raw_copy: Path) -> dict:
    from premiere import build_manifest
    man = build_manifest(project, clips, categories, None, 0.8, None, False)
    work = raw_copy.parent
    out = work / OUT_DIR
    out.mkdir(exist_ok=True)
    rows, mapping, counts = [], {}, {}
    raw_s = str(raw_copy.resolve())
    for c in man["clips"]:
        p = c["path"]
        if not str(Path(p).resolve()).startswith(raw_s + os.sep) or c["camera"] == "music":
            continue
        rel = Path(os.path.relpath(p, raw_s))
        if c["reject"]:
            rows.append([p, "", "", "skipped: cull reject (" + ", ".join(c["reject"]) + ")"])
            continue
        folder = c["flag_bin"] if c.get("flag_bin") else c["bin"]
        stem = _safe("_".join(rel.parts[:-1] + (rel.stem,)))
        st = c.get("steady") or {}
        trim = (st.get("decision") in ("best-cut", "warp") and st.get("range"))
        if trim:
            a, b = st["range"]
            name = f"{stem}_best_{a:05.1f}-{b:05.1f}{rel.suffix}"
        else:
            name = stem + rel.suffix
        dst = out / Path(*[_safe(x) for x in folder.split("/")]) / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() and dst.stat().st_size > 0:
            how = "already there"
        else:
            try:
                how = _trim(Path(p), dst, a, b) if trim else _clone(Path(p), dst)
            except Exception as e:
                rows.append([p, str(dst), folder, f"FAILED: {e}"])
                log(f"bycategory: {rel} failed: {e}")
                continue
        if trim:
            how += f" best cut {a:.1f}-{b:.1f}s"
        mapping[p] = {"path": str(dst), "category_folder": folder, "trimmed": bool(trim),
                      "range": st.get("range") if trim else None}
        rows.append([p, str(dst), folder, how])
        counts[folder] = counts.get(folder, 0) + 1
    logs = work / "logs"
    logs.mkdir(exist_ok=True)
    with open(logs / "bycategory.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["raw_copy", "by_category", "folder", "action"])
        w.writerows(rows)
    save_json(project / "edit" / "assemble" / "bycategory.json", mapping)
    trimmed = sum(1 for v in mapping.values() if v["trimmed"])
    skipped = sum(1 for r in rows if r[3].startswith("skipped"))
    failed = sum(1 for r in rows if r[3].startswith("FAILED"))
    for k in sorted(counts):
        log(f"  {k}: {counts[k]}")
    log(f"BY_CATEGORY: {len(mapping)} clips ({trimmed} shaky Creative clips trimmed to their best cut), "
        f"{skipped} cull rejects left out, {failed} failed -> {out}")
    return {"out": str(out), "clips": len(mapping), "trimmed": trimmed, "skipped": skipped, "failed": failed, "folders": counts}
