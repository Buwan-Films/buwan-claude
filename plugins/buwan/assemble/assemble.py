#!/usr/bin/env python3
"""Buwan assemble — footage prep + music-driven first cut, as files every editing app can import.

  assemble.py scan      <footage dir> --out edit/assemble/clips.json [--music <dir or files...>]
  assemble.py cull      <project>            -> edit/assemble/cull.json
  assemble.py music     <project> --intro <track1> --main <track2>   -> edit/assemble/music.json
  assemble.py sync      <project> [--anchor "2-Main"] [--trusted cam ...]  -> edit/assemble/sync.json + multicams.json
  assemble.py organize  <project> --categories edit/assemble/categories.json  -> edit/organize_vN.fcpxml
  assemble.py selects   <project> --selects edit/assemble/selects.json      -> edit/selects_vN.fcpxml
  assemble.py build     <project> --selects edit/assemble/selects.json [--name "SDE Cut v1"]  -> edit/sde-cut_vN.fcpxml + .edl
  assemble.py selftest  <out dir>   synthetic 3-camera wedding + 2 tracks -> runs everything; import the FCPXML to verify

<project> is a Buwan project folder (…/projects/<date>_<client>_<type>). Footage root comes from edit/SOURCES.md
or --footage. Nothing under the footage root is ever written.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import Clip, scan_media, probe_clip, save_json, load_json, log, slug  # noqa: E402

AUD = {".wav", ".aif", ".aiff", ".mp3", ".m4a", ".flac", ".aac"}


def adir(project: Path) -> Path:
    d = project / "edit" / "assemble"
    d.mkdir(parents=True, exist_ok=True)
    return d


def footage_root(project: Path, override: str | None) -> Path:
    if override:
        return Path(override)
    src = project / "edit" / "SOURCES.md"
    if src.exists():
        for line in src.read_text().splitlines():
            m = re.search(r"(/\S+|[A-Za-z]:\\\S+)", line)
            if m and Path(m.group(1)).exists():
                return Path(m.group(1))
    if (project / "sources" / "footage").exists():
        return project / "sources" / "footage"
    sys.exit("No footage root: pass --footage or write it in edit/SOURCES.md")


def next_version(project: Path, stem: str, ext: str) -> Path:
    n = 1
    while (project / "edit" / f"{stem}_v{n}{ext}").exists():
        n += 1
    return project / "edit" / f"{stem}_v{n}{ext}"


def load_clips(project: Path) -> dict[str, Clip]:
    return {d["path"]: Clip.from_json(d) for d in load_json(adir(project) / "clips.json")}


def load_categories(project: Path, path: str | None) -> dict:
    """{clip path: category}. Accepts categories.json or the organize clip-log.csv."""
    p = Path(path) if path else None
    if p is None:
        for cand in (adir(project) / "categories.json", project / "edit" / "clip-log.csv"):
            if cand.exists():
                p = cand
                break
    if p is None:
        return {}
    if p.suffix == ".json":
        return load_json(p)
    out = {}
    with open(p, newline="") as f:
        for row in csv.DictReader(f):
            out[row.get("path") or row.get("clip")] = row.get("category", "")
    return out


# ---------- commands ----------
def cmd_scan(a):
    project = Path(a.project)
    root = footage_root(project, a.footage)
    log(f"scanning {root}")
    clips = scan_media(root)
    music = []
    for m in a.music or []:
        mp = Path(m)
        files = sorted(x for x in mp.iterdir() if x.suffix.lower() in AUD) if mp.is_dir() else [mp]
        for f in files:
            c = probe_clip(f, f.parent)
            if c:
                c.camera = "music"
                music.append(c)
    save_json(adir(project) / "clips.json", [c.to_json() for c in clips + music])
    cams = sorted({c.camera for c in clips})
    log(f"{len(clips)} clips, cameras: {cams}, music files: {[m.name for m in music]}")
    (project / "edit" / "SOURCES.md").parent.mkdir(parents=True, exist_ok=True)
    if not (project / "edit" / "SOURCES.md").exists():
        (project / "edit" / "SOURCES.md").write_text(f"Footage root (read-only): {root}\n")


def cmd_cull(a):
    from cull import cull
    project = Path(a.project)
    clips = [c for c in load_clips(project).values() if c.camera != "music"]
    res = cull(clips, a.workers)
    save_json(adir(project) / "cull.json", res)
    rej = [r for r in res if r["reject"]]
    log(f"rejected {len(rej)}/{len(res)}: " + ", ".join(f"{r['name']}({'/'.join(r['reject'])})" for r in rej[:20]))


def cmd_music(a):
    from music import analyse_tracks
    project = Path(a.project)
    res = analyse_tracks(a.intro, a.main)
    save_json(adir(project) / "music.json", res)
    for k, v in res.items():
        s = v["sections"]
        log(f"{k}: {v['duration']:.1f}s {v['tempo_bpm']:.0f} bpm | soft 0-{s['intro-soft'][1]}s, peak {s['peak'][0]}-{s['peak'][1]}s, outro from {s['outro'][0]}s")


def cmd_sync(a):
    from sync import sync
    project = Path(a.project)
    clips = [c for c in load_clips(project).values() if c.camera != "music" and c.kind == "video"]
    cull_p = adir(project) / "cull.json"
    rejected = {m["path"] for m in load_json(cull_p) if m["reject"]} if cull_p.exists() else set()
    res = sync(clips, a.anchor, a.trusted, rejected)
    save_json(adir(project) / "sync.json", res)
    # multicam groups: connected components of overlapping synced clips with >= 2 cameras
    placed = [(c, res["clips"][c.path]["offset"]) for c in clips if res["clips"].get(c.path, {}).get("offset") is not None]
    placed.sort(key=lambda x: x[1])
    groups, cur, cur_end = [], [], -1
    for c, off in placed:
        if cur and off > cur_end + 2.0:
            groups.append(cur)
            cur, cur_end = [], -1
        cur.append((c, off))
        cur_end = max(cur_end, off + c.duration)
    if cur:
        groups.append(cur)
    mcs = []
    for g in groups:
        cams = sorted({c.camera for c, _ in g})
        if len(cams) < 2:
            continue
        t0 = min(off for _, off in g)
        span = max(off + c.duration for c, off in g) - t0
        if span < 10:
            continue
        mid = {"id": f"mc{len(mcs)+1}", "name": f"MC {len(mcs)+1:02d} ({', '.join(cams)}) {int(span//60)}m", "duration": round(span, 3),
               "angles": [{"name": cam, "clips": [{"clip": c.path, "offset": round(off - t0, 4)} for c, off in g if c.camera == cam]} for cam in cams]}
        mcs.append(mid)
    save_json(adir(project) / "multicams.json", mcs)
    log(f"{len(mcs)} multicam groups")


def _roles_for(categories: dict, clips: dict[str, Clip]):
    vrole = {"02 Prep & Details": "Video.Details", "03 Portraits": "Video.Portraits", "04 Ceremony": "Video.Ceremony", "05 Reactions & BTS": "Video.Reactions",
             "06 Establishing": "Video.Establishing", "07 Reception & Party": "Video.Party", "08 Drone": "Video.Drone", "11 Graphics": "Titles", "12 Grade & Adjust": "Video.Adjust"}
    roles, vroles = {}, {}
    for p, cat in categories.items():
        if p not in clips:
            continue
        if cat == "01 Speech":
            roles[p] = "dialogue"
        elif cat == "09 Music":
            roles[p] = "music"
        elif cat == "10 SFX & Ambience":
            roles[p] = "effects"
        elif cat in vrole:
            vroles[p] = vrole[cat]
    return roles, vroles


def cmd_organize(a):
    from fcpxml import write_plan
    project = Path(a.project)
    clips = load_clips(project)
    cats = load_categories(project, a.categories)
    cull_res = load_json(adir(project) / "cull.json") if (adir(project) / "cull.json").exists() else []
    rejected = [m["path"] for m in cull_res if m["reject"]]
    notes = {m["path"]: "cull: " + ", ".join(m["reject"] or m["warn"]) for m in cull_res if (m["reject"] or m["warn"])}
    kw = {}
    for p in clips:
        k = [cats[p]] if cats.get(p) else ["unsorted"]
        kw[p] = k
        if p in notes and not any(x in notes[p] for x in ("cull: false", "cull: black", "cull: blown")):
            kw[p].append("warn")
    roles, vroles = _roles_for(cats, clips)
    mcs = load_json(adir(project) / "multicams.json") if (adir(project) / "multicams.json").exists() else []
    plan = {"name": "", "event": a.event or project.name, "library": a.library, "clips": {p: c.to_json() for p, c in clips.items()},
            "keywords": kw, "rejected": rejected, "notes": notes, "roles": roles, "video_roles": vroles, "multicams": mcs if a.multicam else []}
    out = Path(a.out) if a.out else next_version(project, "organize", ".fcpxml")
    write_plan(plan, out)
    log(f"wrote {out}: {len(clips)} clips, {len(rejected)} rejected, {len(plan['multicams'])} multicams")


def _read_selects(path):
    sel = load_json(path)
    for s in sel:
        for k in ("clip", "in", "out"):
            if k not in s:
                sys.exit(f"selects.json entries need clip/in/out: {s}")
    return sel


def cmd_selects(a):
    from fcpxml import write_plan
    project = Path(a.project)
    clips = load_clips(project)
    sel = _read_selects(a.selects)
    mcs = load_json(adir(project) / "multicams.json") if (adir(project) / "multicams.json").exists() else []
    inmc = {cl["clip"]: m["id"] for m in mcs for ang in m["angles"] for cl in ang["clips"]}
    spine, t, last_part, seen = [], 0.0, None, set()
    for s in sel:
        if last_part is not None and s.get("part") != last_part:
            t += 1.5
        d = s["out"] - s["in"]
        mk = [{"t": 0.0, "name": f"{s.get('beat','line')}: {s.get('speaker','')} — {(s.get('text') or '')[:60]}"}]
        if s.get("part") and s["part"] not in seen:
            seen.add(s["part"])
            mk.insert(0, {"t": 0.0, "name": f"PART: {s['part']}", "chapter": True})
        if s.get("beat") in ("vows", "first looks") or s.get("hold"):
            mk.append({"t": 0.0, "name": "HOLD — no cutaways"})
        e = {"clip": s["clip"], "in": s["in"], "out": s["out"], "at": t, "dur": d, "role": "dialogue", "audio_role": f"dialogue.{s.get('speaker') or 'speech'}",
             "name": f"{s.get('beat','')} {s.get('speaker','')}".strip(), "markers": mk}
        if a.multicam and s["clip"] in inmc:
            e["mc"] = inmc[s["clip"]]
        spine.append(e)
        t += d + 0.4
        last_part = s.get("part")
    plan = {"name": a.name or "Story-Lock Selects", "event": a.event or project.name, "library": a.library, "clips": {p: c.to_json() for p, c in clips.items()},
            "spine": spine, "connected": [], "include_event_clips": False, "multicams": [m for m in mcs if a.multicam and m["id"] in {e.get("mc") for e in spine}]}
    out = Path(a.out) if a.out else next_version(project, "selects", ".fcpxml")
    write_plan(plan, out)
    log(f"wrote {out}: {len(spine)} lines, {t:.1f}s")


def cmd_build(a):
    from fcpxml import write_plan
    from timeline import build_plan, picture_edl
    project = Path(a.project)
    clips = load_clips(project)
    cats = load_categories(project, a.categories)
    cull_res = load_json(adir(project) / "cull.json") if (adir(project) / "cull.json").exists() else []
    music = load_json(adir(project) / "music.json")
    for k in ("intro", "main"):
        if k in music and music[k]["path"] not in clips:
            c = probe_clip(Path(music[k]["path"]), Path(music[k]["path"]).parent)
            c.camera = "music"
            clips[c.path] = c
    sel = _read_selects(a.selects)
    sync = load_json(adir(project) / "sync.json") if (adir(project) / "sync.json").exists() else None
    mcs = load_json(adir(project) / "multicams.json") if (adir(project) / "multicams.json").exists() else []
    inmc = {cl["clip"]: m["id"] for m in mcs for ang in m["angles"] for cl in ang["clips"]}
    if a.multicam:
        for s in sel:
            if s["clip"] in inmc:
                s["mc"] = inmc[s["clip"]]
    opts = json.loads(a.options) if a.options else {}
    plan = build_plan(clips, cats, cull_res, music, sel, sync, a.name or "SDE Cut", a.event or project.name, a.library, opts)
    plan["multicams"] = [m for m in mcs if a.multicam and m["id"] in {e.get("mc") for e in plan["spine"]}]
    out = Path(a.out) if a.out else next_version(project, slug(a.name or "sde-cut"), ".fcpxml")
    write_plan(plan, out)
    save_json(out.with_suffix(".plan.json"), {k: v for k, v in plan.items() if k != "clips"})
    edl = picture_edl(plan, str(out.with_suffix(".edl")))
    try:
        from editmap import draw_map
        png = draw_map(plan, music, cats, str(out.with_suffix(".map.png")))
        log(f"  edit map: {png}")
    except Exception as e:
        log(f"  (edit map skipped: {e})")
    st = plan["stats"]
    log(f"wrote {out}\n  total {st['total_s']}s (intro {st['intro_s']}s + story {st['main_s']}s), {st['speech_lines']} lines, {st['broll_shots']} b-roll shots\n  picture EDL for the proof gate: {edl}")
    for n in plan["notes"]:
        log("  " + n)


def cmd_selftest(a):
    from selftest import run_selftest
    run_selftest(Path(a.out))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan"); s.add_argument("project"); s.add_argument("--footage"); s.add_argument("--music", nargs="*"); s.set_defaults(f=cmd_scan)
    s = sub.add_parser("cull"); s.add_argument("project"); s.add_argument("--workers", type=int, default=4); s.set_defaults(f=cmd_cull)
    s = sub.add_parser("music"); s.add_argument("project"); s.add_argument("--intro"); s.add_argument("--main", required=True); s.set_defaults(f=cmd_music)
    s = sub.add_parser("sync"); s.add_argument("project"); s.add_argument("--anchor"); s.add_argument("--trusted", nargs="*"); s.set_defaults(f=cmd_sync)
    for name, fn in (("organize", cmd_organize), ("selects", cmd_selects), ("build", cmd_build)):
        s = sub.add_parser(name); s.add_argument("project"); s.add_argument("--out"); s.add_argument("--event"); s.add_argument("--library")
        s.add_argument("--multicam", action="store_true"); s.add_argument("--categories")
        if name != "organize":
            s.add_argument("--selects", required=True); s.add_argument("--name")
        if name == "build":
            s.add_argument("--options", help='JSON, e.g. {"music_bed_db":-18}')
        s.set_defaults(f=fn)
    s = sub.add_parser("selftest"); s.add_argument("out"); s.set_defaults(f=cmd_selftest)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
