#!/usr/bin/env python3
"""Buwan assemble — footage prep + music-driven first cut, as files every editing app can import.

  assemble.py workcopy  <project> --source <raw clips folder> [--to <WORK folder>]   -> RAW_COPY next to the raw folder, verified, duplicates skipped
  assemble.py dedupe    <project> [--footage <dir>]  -> edit/assemble/dedupe.json + dedupe_report.md (reference-in-place jobs)
  assemble.py scan      <project> [--footage <dir>] [--music <dir or files...>] [--dedupe]  -> edit/assemble/clips.json
  assemble.py cull      <project>            -> edit/assemble/cull.json
  assemble.py steady    <project>            -> edit/assemble/steady.json  (shaky Creative/Glider clips: best cut first | warp (gimbal only, on the best cut) | handheld | too shaky)
  assemble.py music     <project> --intro <track1> --main <track2>   -> edit/assemble/music.json
  assemble.py sync      <project> [--anchor "2-Main"] [--trusted cam ...]  -> edit/assemble/sync.json + multicams.json
  assemble.py bycategory <project>           -> <WORK>/BY_CATEGORY/<category>[/<sub-bin>]/ (APFS clones of RAW_COPY; rejects left out; shaky Creative clips trimmed to their best cut)
  assemble.py exposure  <project>            -> edit/assemble/exposure.json (per-clip exposure fix applied before the look)
  assemble.py organize  <project> --categories edit/assemble/categories.json  -> edit/organize_vN.fcpxml
  assemble.py selects   <project> --selects edit/assemble/selects.json      -> edit/selects_vN.fcpxml
  assemble.py build     <project> --selects edit/assemble/selects.json [--name "SDE Cut v1"]  -> edit/sde-cut_vN.fcpxml + .edl
  assemble.py handoff   <project> [--title "Marynhor & Jomar"]  -> EDITOR_START_HERE.md in the WORK folder (or the project)
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
    if a.dedupe:
        from workcopy import find_duplicates, write_dedupe_report
        _, dups = find_duplicates(root)
        skip = {str(d) for d in dups}
        before = len(clips)
        clips = [c for c in clips if c.path not in skip]
        save_json(adir(project) / "dedupe.json", {str(d): str(o) for d, o in dups.items()})
        write_dedupe_report(adir(project) / "dedupe_report.md", root, dups, "Duplicate footage (left out of the scan)")
        log(f"dedupe: {before - len(clips)} byte-identical duplicates left out -> {adir(project) / 'dedupe_report.md'}")
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


def cmd_steady(a):
    from steady import steady
    project = Path(a.project)
    clips = [c for c in load_clips(project).values() if c.camera != "music"]
    cull_res = load_json(adir(project) / "cull.json") if (adir(project) / "cull.json").exists() else []
    if not cull_res:
        sys.exit("run cull first (steady reads the heavy-motion flags)")
    gp = project / "edit" / "assemble" / "gimbal.txt"
    pats = (gp.read_text().splitlines() if gp.exists() else []) + list(a.gimbal or [])
    res = steady(clips, cull_res, a.workers, pats)
    save_json(adir(project) / "steady.json", res)
    rep = [f"# Shaky Creative/Glider footage — decisions", "",
           "Best cut first; only gimbal shots are stabilized, and only on their best cut. Gimbal shots: "
           + (", ".join(f"`{x.strip()}`" for x in pats if x.strip() and not x.strip().startswith("#")) or "by camera name only (none listed in `edit/assemble/gimbal.txt`)"), "",
           "| Clip | Gimbal | Decision | Range | Why |", "|---|---|---|---|---|"]
    for v in sorted(res.values(), key=lambda x: x["name"]):
        rng = f"{v['range'][0]:.1f}–{v['range'][1]:.1f}s" if v.get("range") else ""
        rep.append(f"| {v['name']} | {'yes' if v.get('gimbal') else 'no'} | {v['decision']} | {rng} | {v.get('reason','')} |")
    (project / "edit" / "steady_report.md").write_text("\n".join(rep) + "\n")
    log(f"wrote {adir(project) / 'steady.json'} and edit/steady_report.md")


def cmd_bycategory(a):
    from bycategory import build
    from workcopy import _footage_root, _protect
    project = Path(a.project)
    raw = Path(a.raw).resolve() if a.raw else _footage_root(project).resolve()
    if raw.name != "RAW_COPY":
        sys.exit(f"bycategory works from the working copy (RAW_COPY); the footage root is {raw}. Run workcopy first.")
    res = build(project, load_clips(project), load_categories(project, a.categories), raw)
    _protect(Path(res["out"]))


def cmd_exposure(a):
    from exposure import exposure
    project = Path(a.project)
    clips = [c for c in load_clips(project).values() if c.camera != "music"]
    cull_res = load_json(adir(project) / "cull.json") if (adir(project) / "cull.json").exists() else []
    ep = adir(project) / "exposure.json"
    res = exposure(clips, load_categories(project, a.categories), {m["path"] for m in cull_res if m["reject"]}, a.workers,
                   a.look, None if a.remeasure or not ep.exists() else load_json(ep))
    save_json(adir(project) / "exposure.json", res)
    rep = ["# Exposure before the look", "", "| Clip | Camera | Avg luma | Fix (EV) | Why |", "|---|---|---|---|---|"]
    for v in sorted(res.values(), key=lambda x: (-abs(x["ev"]), x["name"])):
        if v["ev"] or v.get("low_key"):
            rep.append(f"| {v['name']} | {v['camera']} | {v.get('yavg', '')} | {v['ev']:+.2f} | {v['reason']} |")
    (project / "edit" / "exposure_report.md").write_text("\n".join(rep) + "\n")
    log(f"wrote {adir(project) / 'exposure.json'} and edit/exposure_report.md")


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


def _speech_clips(project: Path, clips: dict[str, Clip], categories: dict) -> list[Clip]:
    sp = [c for p, c in clips.items() if categories.get(p) == "01 Speech" and c.has_audio]
    return sp or [c for c in clips.values() if c.has_audio and c.camera != "music"]


def cmd_enhance(a):
    from enhance import enhance, render_clean
    project = Path(a.project)
    clips = load_clips(project)
    cats = load_categories(project, a.categories)
    sp = _speech_clips(project, clips, cats)
    res = enhance(sp, a.workers)
    if a.render:
        for c in sp:
            if res.get(c.path, {}).get("recipe"):
                res[c.path]["clean"] = render_clean(c, res[c.path]["measure"], project / "edit" / "audio" / "clean")
    save_json(adir(project) / "enhance.json", res)
    noisy = [Path(p).name for p, v in res.items() if v.get("measure", {}).get("snr_db") is not None and v["measure"]["snr_db"] < 15]
    log(f"measured {len(res)} speech clips; noisy (SNR<15dB): {noisy[:15]}")


def cmd_deadair(a):
    from deadair import dead_air
    project = Path(a.project)
    clips = load_clips(project)
    cats = load_categories(project, a.categories)
    res = dead_air(_speech_clips(project, clips, cats), a.workers)
    save_json(adir(project) / "speech_ranges.json", res)
    log(f"speech kept {sum(v['kept_s'] for v in res.values())/60:.1f} min, dead air removed {sum(v['removed_s'] for v in res.values())/60:.1f} min")


def _grade_opt(a):
    if not getattr(a, "grade", None):
        return None
    lut = {"warm": "Buwan_Warm", "cool": "Buwan_Cool", "bw": "Buwan_BW"}.get(a.grade.lower(), a.grade)
    return {"lut": lut, "mix": a.lut_mix, "fcp_filter": bool(a.fcp_lut)}


def _enhance_opt(project: Path, a):
    p = adir(project) / "enhance.json"
    if getattr(a, "no_enhance", False) or not p.exists():
        return {}
    return {k: v["recipe"] for k, v in load_json(p).items() if v.get("recipe")}


def cmd_aroll(a):
    """A-Roll clean: every speech clip, silences removed, in sync/time order, enhanced."""
    from fcpxml import write_plan
    project = Path(a.project)
    clips = load_clips(project)
    cats = load_categories(project, a.categories)
    rp = adir(project) / "speech_ranges.json"
    if not rp.exists():
        sys.exit("run `deadair` first")
    ranges = load_json(rp)
    sync = load_json(adir(project) / "sync.json") if (adir(project) / "sync.json").exists() else {"clips": {}}
    order = sorted(ranges.keys(), key=lambda p: (sync["clips"].get(p, {}).get("offset") if sync["clips"].get(p, {}).get("offset") is not None else 1e12, clips[p].rel if p in clips else p))
    spine, t = [], 0.0
    for p in order:
        if p not in clips:
            continue
        for a0, b0 in ranges[p]["ranges"]:
            d = b0 - a0
            spine.append({"clip": p, "in": a0, "out": b0, "at": t, "dur": d, "role": "dialogue", "audio_role": f"dialogue.{clips[p].camera or 'speech'}",
                          "name": clips[p].name, "markers": [{"t": 0.0, "name": f"{clips[p].name} {a0:.1f}s"}]})
            t += d + 0.3
    plan = {"name": a.name or "A-Roll clean", "event": a.event or project.name, "library": a.library, "clips": {p: c.to_json() for p, c in clips.items()},
            "spine": spine, "connected": [], "include_event_clips": False, "enhance": _enhance_opt(project, a), "grade": _grade_opt(a)}
    out = Path(a.out) if a.out else next_version(project, "aroll-clean", ".fcpxml")
    write_plan(plan, out)
    log(f"wrote {out}: {len(spine)} speech segments, {t/60:.1f} min (dead air removed)")


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
    from premiere import sub_bin
    sp_ = adir(project) / "subbins.json"
    subs = load_json(sp_) if sp_.exists() else {}
    kw = {}
    for p in clips:
        k = [cats[p]] if cats.get(p) else ["unsorted"]
        sb = sub_bin(cats.get(p, ""), subs.get(p))
        if sb:
            k.append(sb)            # Final Cut: a keyword collection per sub-bin (e.g. "Bride prep")
        kw[p] = k
        if p in notes and not any(x in notes[p] for x in ("cull: false", "cull: black", "cull: blown")):
            kw[p].append("warn")
    roles, vroles = _roles_for(cats, clips)
    mcs = load_json(adir(project) / "multicams.json") if (adir(project) / "multicams.json").exists() else []
    rp = adir(project) / "speech_ranges.json"
    favorites = {p: [[a, b, "speech"] for a, b in v["ranges"]] for p, v in load_json(rp).items()} if rp.exists() else {}
    sp = adir(project) / "steady.json"
    for p, v in (load_json(sp).items() if sp.exists() else []):
        if v["decision"] == "best-cut":
            favorites.setdefault(p, []).append([v["range"][0], v["range"][1], "steady"])
            kw.setdefault(p, []).append("steady pick")
            notes[p] = (notes.get(p, "") + "; " if notes.get(p) else "") + f"steady pick {v['range'][0]:.1f}-{v['range'][1]:.1f}s"
        elif v["decision"] == "warp":
            kw.setdefault(p, []).append("stabilize")
            rg = f" on the best cut {v['range'][0]:.1f}-{v['range'][1]:.1f}s" if v.get("range") else ""
            if v.get("range"):
                favorites.setdefault(p, []).append([v["range"][0], v["range"][1], "stabilize"])
            notes[p] = (notes.get(p, "") + "; " if notes.get(p) else "") + f"gimbal: tick Stabilization in the Inspector{rg}"
    plan = {"name": "", "event": a.event or project.name, "library": a.library, "clips": {p: c.to_json() for p, c in clips.items()},
            "keywords": kw, "rejected": rejected, "notes": notes, "roles": roles, "video_roles": vroles, "multicams": mcs if a.multicam else [],
            "favorites": favorites}
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
            "spine": spine, "connected": [], "include_event_clips": False, "multicams": [m for m in mcs if a.multicam and m["id"] in {e.get("mc") for e in spine}],
            "enhance": _enhance_opt(project, a), "grade": _grade_opt(a)}
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
    plan["enhance"] = _enhance_opt(project, a)
    plan["grade"] = _grade_opt(a)
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


def cmd_premiere(a):
    from premiere import cmd_premiere as run_premiere
    project = Path(a.project)
    clips = load_clips(project)
    for k, v in (load_json(adir(project) / "music.json") if (adir(project) / "music.json").exists() else {}).items():
        if isinstance(v, dict) and v.get("path") and v["path"] not in clips:
            c = probe_clip(Path(v["path"]), Path(v["path"]).parent)
            if c:
                c.camera = "music"
                clips[c.path] = c
    run_premiere(a, clips, load_categories(project, a.categories))


def cmd_selftest(a):
    from selftest import run_selftest
    run_selftest(Path(a.out))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("workcopy", help="copy the raw clips into <raw>_WORK/RAW_COPY on the same drive, verified, duplicates skipped; the project then reads from the copy")
    s.add_argument("project"); s.add_argument("--source", required=True, help="the raw clips folder on the SSD (read-only)")
    s.add_argument("--to", help="WORK folder (default: <source>_WORK next to the source)")
    s.add_argument("--all-files", action="store_true", help="copy every file, not only media")
    s.add_argument("--force", action="store_true", help="skip the free-space check")
    s.set_defaults(f=lambda a: __import__("workcopy").cmd_workcopy(a))
    s = sub.add_parser("dedupe"); s.add_argument("project"); s.add_argument("--footage"); s.set_defaults(f=lambda a: __import__("workcopy").cmd_dedupe(a))
    s = sub.add_parser("handoff"); s.add_argument("project"); s.add_argument("--title"); s.add_argument("--out"); s.set_defaults(f=lambda a: __import__("workcopy").cmd_handoff(a))
    s = sub.add_parser("scan"); s.add_argument("project"); s.add_argument("--footage"); s.add_argument("--music", nargs="*")
    s.add_argument("--dedupe", action="store_true", help="leave byte-identical duplicates out of the scan (reference-in-place jobs)"); s.set_defaults(f=cmd_scan)
    s = sub.add_parser("cull"); s.add_argument("project"); s.add_argument("--workers", type=int, default=4); s.set_defaults(f=cmd_cull)
    s = sub.add_parser("steady"); s.add_argument("project"); s.add_argument("--workers", type=int, default=4)
    s.add_argument("--gimbal", nargs="*", help="clips shot on a gimbal: card folders, clip names or globs (added to edit/assemble/gimbal.txt patterns); '*' = all Creative clips")
    s.set_defaults(f=cmd_steady)
    s = sub.add_parser("bycategory"); s.add_argument("project"); s.add_argument("--raw", help="the RAW_COPY folder (default: from edit/SOURCES.md)"); s.add_argument("--categories"); s.set_defaults(f=cmd_bycategory)
    s = sub.add_parser("exposure"); s.add_argument("project"); s.add_argument("--categories"); s.add_argument("--workers", type=int, default=6)
    s.add_argument("--look", default="warm", choices=["warm", "cool", "bw"]); s.add_argument("--remeasure", action="store_true", help="read the footage again instead of reusing exposure.json"); s.set_defaults(f=cmd_exposure)
    s = sub.add_parser("music"); s.add_argument("project"); s.add_argument("--intro"); s.add_argument("--main", required=True); s.set_defaults(f=cmd_music)
    s = sub.add_parser("sync"); s.add_argument("project"); s.add_argument("--anchor"); s.add_argument("--trusted", nargs="*"); s.set_defaults(f=cmd_sync)
    s = sub.add_parser("enhance"); s.add_argument("project"); s.add_argument("--categories"); s.add_argument("--workers", type=int, default=4); s.add_argument("--render", action="store_true", help="also write cleaned WAVs to edit/audio/clean"); s.set_defaults(f=cmd_enhance)
    s = sub.add_parser("deadair"); s.add_argument("project"); s.add_argument("--categories"); s.add_argument("--workers", type=int, default=4); s.set_defaults(f=cmd_deadair)
    for name, fn in (("organize", cmd_organize), ("selects", cmd_selects), ("build", cmd_build), ("aroll", cmd_aroll)):
        s = sub.add_parser(name); s.add_argument("project"); s.add_argument("--out"); s.add_argument("--event"); s.add_argument("--library")
        s.add_argument("--multicam", action="store_true"); s.add_argument("--categories")
        s.add_argument("--grade", help="warm | cool | bw — tag the timeline with the studio look"); s.add_argument("--lut-mix", type=float, default=0.8)
        s.add_argument("--fcp-lut", action="store_true", help="EXPERIMENTAL: write Final Cut's Custom LUT effect on every camera clip")
        s.add_argument("--no-enhance", action="store_true")
        if name in ("selects", "build"):
            s.add_argument("--selects", required=True)
        if name != "organize":
            s.add_argument("--name")
        if name == "build":
            s.add_argument("--options", help='JSON, e.g. {"music_bed_db":-18}')
        s.set_defaults(f=fn)
    s = sub.add_parser("premiere", help="write edit/premiere/manifest.json for the Premiere apply library (buwan-premiere/jsx/buwan.jsx)")
    s.add_argument("project"); s.add_argument("--plan", help="a *.plan.json written by `build` — adds the timeline to the manifest")
    s.add_argument("--categories"); s.add_argument("--grade", help="warm | cool | bw"); s.add_argument("--lut-mix", type=float, default=0.8)
    s.add_argument("--use-clean", action="store_true", help="build lays the cleaned WAVs (enhance --render) under each speech clip")
    s.add_argument("--no-flags", action="store_true", help="keep shaky/soft/dark clips in their category bins instead of 00 Flagged/<reason>")
    s.add_argument("--skeleton", help="name of the empty SDE assembly sequence the skeleton step creates (default SDE_ASSEMBLY_v1)")
    s.add_argument("--out"); s.set_defaults(f=cmd_premiere)
    s = sub.add_parser("selftest"); s.add_argument("out"); s.set_defaults(f=cmd_selftest)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
