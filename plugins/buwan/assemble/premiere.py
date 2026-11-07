"""Premiere Pro manifest: everything the engine decided, in one JSON the Premiere apply
library (plugins/buwan-premiere/jsx/buwan.jsx) reads inside Premiere through the bridge.

  assemble.py premiere <project> [--plan edit/sde-cut_v1.plan.json] [--grade warm|cool|bw]
                                 [--lut-mix 0.8] [--categories ...] [--out edit/premiere/manifest.json]

The manifest is plain JSON that ExtendScript (ES3, no JSON object) can eval, so it holds
only strings, numbers, booleans, arrays and objects — no NaN/Infinity.
"""
from __future__ import annotations

import datetime as _dt
import math
from pathlib import Path

from common import Clip, load_json, save_json, log

# Premiere label indices (premiere-pro-mcp set_color_label table):
# 0 Violet 1 Iris 2 Caribbean 3 Lavender 4 Cerulean 5 Forest 6 Rose 7 Mango
# 8 Purple 9 Blue 10 Teal 11 Magenta 12 Tan 13 Green 14 Brown 15 Yellow
LABELS = {
    "01 Speech": 7,              # Mango
    "02 Prep & Details": 12,     # Tan
    "03 Portraits": 15,          # Yellow
    "04 Ceremony": 0,            # Violet
    "05 Reactions & BTS": 6,     # Rose
    "06 Establishing": 4,        # Cerulean
    "07 Reception & Party": 11,  # Magenta
    "08 Drone": 10,              # Teal
    "09 Music": 5,               # Forest
    "10 SFX & Ambience": 2,      # Caribbean
    "11 Graphics": 3,            # Lavender
    "12 Grade & Adjust": 14,     # Brown
}
LABEL_NAMES = ["Violet", "Iris", "Caribbean", "Lavender", "Cerulean", "Forest", "Rose", "Mango",
               "Purple", "Blue", "Teal", "Magenta", "Tan", "Green", "Brown", "Yellow"]
REJECT_BIN = "00 Rejected (cull)"
REJECT_LABEL = 14  # Brown
NO_GRADE = {"09 Music", "10 SFX & Ambience", "11 Graphics", "12 Grade & Adjust"}
LUT_FILES = {"warm": "Buwan_Warm", "cool": "Buwan_Cool", "bw": "Buwan_BW"}


def _clean(v):
    """Make a value safe for ES3 eval: no NaN/inf, tuples -> lists."""
    if isinstance(v, float):
        return None if (math.isnan(v) or math.isinf(v)) else round(v, 4)
    if isinstance(v, dict):
        return {str(k): _clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    return v


def find_lut(project: Path, look: str) -> str | None:
    name = LUT_FILES.get(look.lower(), look) + ".cube"
    cands = [
        project.parent.parent / "kit" / "luts" / name,          # <workspace>/kit/luts (installed by setup-kit)
        Path.home() / ".buwan" / "kit" / "luts" / name,
        Path(__file__).resolve().parent.parent / "kit" / "luts" / name,  # plugin copy
    ]
    for c in cands:
        if c.exists():
            return str(c.resolve())
    return None


def _load_optional(p: Path, default):
    return load_json(p) if p.exists() else default


def build_manifest(project: Path, clips: dict[str, Clip], categories: dict, grade: str | None, lut_mix: float,
                   plan_path: Path | None, use_clean: bool) -> dict:
    adir = project / "edit" / "assemble"
    cull = {m["path"]: m for m in _load_optional(adir / "cull.json", [])}
    sync = _load_optional(adir / "sync.json", {"clips": {}})
    multicams = _load_optional(adir / "multicams.json", [])
    enhance = _load_optional(adir / "enhance.json", {})
    ranges = _load_optional(adir / "speech_ranges.json", {})
    music = _load_optional(adir / "music.json", {})

    out_clips = []
    for p, c in clips.items():
        cat = categories.get(p) or ("09 Music" if c.camera == "music" else "")
        cm = cull.get(p, {})
        rej = list(cm.get("reject") or [])
        entry = {
            "path": p, "name": c.name, "camera": c.camera, "kind": c.kind, "duration": round(c.duration, 3),
            "fps": round(c.fps_num / c.fps_den, 3) if c.fps_num else 0, "has_audio": bool(c.has_audio),
            "category": cat,
            "bin": REJECT_BIN if rej else (cat or ("Footage/" + c.camera if c.camera else "Footage")),
            "label": REJECT_LABEL if rej else LABELS.get(cat, -1),
            "reject": rej, "warn": list(cm.get("warn") or []),
            "sync_offset": (sync["clips"].get(p) or {}).get("offset"),
            "speech_ranges": (ranges.get(p) or {}).get("ranges") or [],
        }
        e = enhance.get(p) or {}
        if e.get("recipe"):
            r = e["recipe"]
            entry["enhance"] = {"gain_db": r.get("gain_db", 0), "noise_reduction": r.get("noise_reduction", 0),
                                "voice_isolation": r.get("voice_isolation", 0), "lufs": (e.get("measure") or {}).get("lufs"),
                                "snr_db": (e.get("measure") or {}).get("snr_db"), "clean": e.get("clean"), "notes": r.get("notes", [])}
        out_clips.append(entry)

    m = {
        "version": 1,
        "generated": _dt.datetime.now().isoformat(timespec="seconds"),
        "project": project.name,
        "project_dir": str(project.resolve()),
        "sequence": {"fps": 23.976, "width": 1920, "height": 1080, "timecode_start": "01:00:00:00"},
        "labels": LABELS, "label_names": LABEL_NAMES, "reject_bin": REJECT_BIN,
        "bins": sorted(set(LABELS) | {REJECT_BIN}),
        "clips": out_clips,
        "multicams": multicams,
        "music": {k: {"path": v["path"], "duration": v["duration"], "tempo_bpm": v.get("tempo_bpm"), "sections": v.get("sections")}
                  for k, v in music.items() if isinstance(v, dict) and "path" in v},
        "grade": None,
        "plan": None,
        "use_clean": use_clean,
        "counts": {"clips": len(out_clips), "rejected": sum(1 for c in out_clips if c["reject"]),
                   "speech": sum(1 for c in out_clips if c["category"] == "01 Speech"),
                   "enhanced": sum(1 for c in out_clips if c.get("enhance")),
                   "with_speech_ranges": sum(1 for c in out_clips if c["speech_ranges"])},
    }
    if grade:
        lut = find_lut(project, grade)
        if not lut:
            log(f"WARNING: LUT for '{grade}' not found — run /buwan:setup-kit (kit/luts). Grade step will be skipped.")
        m["grade"] = {"look": grade, "lut": lut, "mix": lut_mix, "intensity": int(round(lut_mix * 100)),
                      "skip_categories": sorted(NO_GRADE)}
    if plan_path:
        plan = load_json(plan_path)
        m["plan"] = {
            "name": plan.get("name", "SDE Cut"), "file": str(plan_path.resolve()),
            "spine": [s for s in plan.get("spine", [])],
            "connected": [c for c in plan.get("connected", [])],
            "stats": plan.get("stats", {}), "notes": plan.get("notes", []),
            "edl": str(plan_path.with_suffix("").with_suffix(".edl").resolve()) if plan_path.with_suffix("").with_suffix(".edl").exists() else None,
        }
    return _clean(m)


def cmd_premiere(a, clips: dict[str, Clip], categories: dict):
    project = Path(a.project)
    plan_path = Path(a.plan) if a.plan else None
    if plan_path and not plan_path.exists():
        raise SystemExit(f"plan not found: {plan_path}")
    m = build_manifest(project, clips, categories, a.grade, a.lut_mix, plan_path, bool(a.use_clean))
    out = Path(a.out) if a.out else project / "edit" / "premiere" / "manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    save_json(out, m)
    c = m["counts"]
    log(f"wrote {out}\n  {c['clips']} clips ({c['rejected']} rejected, {c['speech']} speech, {c['enhanced']} with sound recipes, "
        f"{c['with_speech_ranges']} with speech ranges), {len(m['multicams'])} multicam groups"
        + (f", grade {m['grade']['look']} -> {m['grade']['lut']}" if m.get('grade') else "")
        + (f", plan {m['plan']['name']} ({len(m['plan']['spine'])} spine items, {len(m['plan']['connected'])} connected)" if m.get('plan') else ""))
    log("  next, in Premiere (through the bridge): $.evalFile(\"<buwan-premiere>/jsx/buwan.jsx\"); return __result(BUWAN.run(\"organize\", \"" + str(out) + "\"));")
    return out
