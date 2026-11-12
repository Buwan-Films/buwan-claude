"""One-command import of the basics' _ENHANCED_ folder into Premiere Pro.

  assemble.py premiere-import <project> [--folder <raw>_ENHANCED_<date-time>]  -> edit/premiere/enhanced.json

The bridge step `enhanced` (buwan-premiere/jsx/buwan.jsx) reads it inside the open project:
  - imports every enhanced clip not in the project yet into  ENHANCED <date-time>/<camera>  (the folder's own layout,
    one bin per camera; cards are not split into bins), 300 per call
  - house label colours where the basics know the category: Drone cameras Teal (08 Drone), clips with speech
    Mango (01 Speech, from /buwan:sync's transcripts)
  - Description column: what the clip sounds like + its first words (searchable in the Project panel), or
    "smoothed (best cut)" for the shaky Creative/Glider clips
  - clips imported earlier only get their label and Description when a transcript arrived later; nothing the editor
    moved, renamed or relabelled is changed. No sequences are made.
"""
from __future__ import annotations

import csv
from pathlib import Path

from common import Clip, load_json, log, save_json

MANGO, TEAL = 7, 10
VIDEO_EXT = {".mov", ".mp4", ".mxf", ".m4v", ".avi", ".mts"}
AERIAL = ("drone", "dji", "aerial", "mavic")


def find_folder(project: Path, folder: str | None) -> Path:
    if folder:
        f = Path(folder)
        if not f.is_dir():
            raise SystemExit(f"not a folder: {f}")
        return f
    from workcopy import _footage_root
    wc_p = project / "edit" / "assemble" / "workcopy.json"
    wc = load_json(wc_p) if wc_p.exists() else {}
    src = Path(wc.get("source") or wc.get("raw_copy") or _footage_root(project))
    runs = sorted(src.parent.glob(f"{src.name}_ENHANCED_*"), key=lambda d: d.name)
    runs = [r for r in runs if r.is_dir()]
    if not runs:
        raise SystemExit(f"no {src.name}_ENHANCED_* folder next to {src} - run /buwan:basics first")
    return runs[-1]


def build(project: Path, clips: dict[str, Clip], folder: Path) -> dict:
    ad = project / "edit" / "assemble"
    tr = load_json(ad / "transcripts.json") if (ad / "transcripts.json").exists() else {}
    kinds = {}
    if (folder / "render_log.csv").exists():
        with open(folder / "render_log.csv", newline="") as f:
            for row in csv.DictReader(f):
                kinds[str(Path(row.get("enhanced", "")))] = row.get("kind")
    stamp = folder.name.split("_ENHANCED_")[-1] if "_ENHANCED_" in folder.name else folder.name
    root_bin = f"ENHANCED {stamp}"
    by_rel = {str(Path(c.rel).with_suffix("")): (p, c) for p, c in clips.items() if c.rel}
    out, seen = [], set()
    vids = [f for f in folder.rglob("*") if f.is_file() and f.suffix.lower() in VIDEO_EXT]
    for mov in sorted(vids):   # rendered .mov + the clips with no fix, copied with their own extension
        if ".part." in mov.name or mov.name.startswith("._"):
            continue
        rel = mov.relative_to(folder)
        raw_p, c = by_rel.get(str(rel.with_suffix("")), (None, None))
        camera = rel.parts[0] if len(rel.parts) > 1 else "clips"
        t = tr.get(raw_p) or {}
        label, desc = -1, ""
        if any(k in camera.lower() for k in AERIAL):
            label = TEAL
        if t.get("speech"):
            label = MANGO
            desc = f"{t.get('hint') or 'talk'}: {t.get('text', '')[:300]}"
        elif kinds.get(str(mov)) == "shaky":
            desc = "smoothed (best cut)"
        out.append({"path": str(mov), "name": mov.name, "bin": f"{root_bin}/{camera}", "label": label, "desc": desc,
                    "speech": bool(t.get("speech")), "srt": t.get("srt") if t.get("speech") else None, "raw": raw_p})
        seen.add(str(mov))
    m = {"version": 1, "kind": "enhanced", "folder": str(folder), "root_bin": root_bin, "clips": out,
         "counts": {"clips": len(out), "speech": sum(1 for c in out if c["speech"]), "drone": sum(1 for c in out if c["label"] == TEAL),
                    "smoothed": sum(1 for c in out if c["desc"] == "smoothed (best cut)"),
                    "cameras": sorted({c["bin"].split("/", 1)[1] for c in out})}}
    return m


def cmd(a, clips: dict[str, Clip]):
    project = Path(a.project)
    folder = find_folder(project, a.folder)
    m = build(project, clips, folder)
    out = Path(a.out) if a.out else project / "edit" / "premiere" / "enhanced.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    save_json(out, m)
    c = m["counts"]
    log(f"wrote {out}\n  {c['clips']} enhanced clips from {folder.name} -> bin '{m['root_bin']}' ({', '.join(c['cameras'])}); "
        f"{c['speech']} with speech (Mango), {c['drone']} drone (Teal), {c['smoothed']} smoothed")
    log(f"  next, through the bridge: node <buwan-premiere>/scripts/premiere-snippet.js enhanced \"{out}\"")
    return out
