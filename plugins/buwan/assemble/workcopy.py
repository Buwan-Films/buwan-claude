"""Working copy on the drive, byte-identical duplicates, and the editor hand-off note.

  workcopy  — copy the raw clips into a sibling WORK folder on the same drive (RAW_COPY/),
              skipping byte-identical duplicates, verifying every copy by SHA-256, and pointing
              the project at the copy. The originals are never read again after this.
  dedupe    — find byte-identical files under the footage root (for reference-in-place jobs).
  handoff   — write EDITOR_START_HERE.md from what the engine produced.

Nothing here deletes, moves or renames anything. Duplicates are *skipped*, not removed.
"""
from __future__ import annotations

import csv
import datetime as _dt
import hashlib
import os
import shutil
import sys
from pathlib import Path

from common import VIDEO_EXT, AUDIO_EXT, log, save_json, load_json

MEDIA_EXT = VIDEO_EXT | AUDIO_EXT
CHUNK = 8 * 1024 * 1024
WORK_SUBDIRS = ("RAW_COPY", "PROJECT", "AUDIO_CLEAN", "EXPORTS", "logs")
PROTECTED_LIST = Path.home() / ".buwan" / "protected-paths.txt"


# ---------- hashing ----------
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def quick_key(path: Path) -> str:
    """size + first/last 1 MB: cheap pre-filter so only same-size candidates get a full hash."""
    size = path.stat().st_size
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read(1024 * 1024))
        if size > 2 * 1024 * 1024:
            f.seek(-1024 * 1024, os.SEEK_END)
            h.update(f.read(1024 * 1024))
    return f"{size}:{h.hexdigest()}"


def media_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*") if p.is_file() and not p.name.startswith(".") and p.suffix.lower() in MEDIA_EXT)


def find_duplicates(root: Path) -> tuple[dict[Path, str], dict[Path, Path]]:
    """Returns (hash per file, duplicate -> original). The first file in sorted path order is the original."""
    files = media_files(root)
    by_quick: dict[str, list[Path]] = {}
    for p in files:
        by_quick.setdefault(quick_key(p), []).append(p)
    hashes: dict[Path, str] = {}
    dups: dict[Path, Path] = {}
    for group in by_quick.values():
        if len(group) == 1:
            continue
        seen: dict[str, Path] = {}
        for p in group:
            h = sha256(p)
            hashes[p] = h
            if h in seen:
                dups[p] = seen[h]
            else:
                seen[h] = p
    return hashes, dups


def write_dedupe_report(path: Path, root: Path, dups: dict[Path, Path], title: str) -> None:
    lines = [f"# {title}", "", f"Scanned: `{root}`  ", f"Byte-identical duplicates found: **{len(dups)}** (skipped, nothing deleted)", ""]
    if dups:
        lines += ["| Skipped | Identical to |", "|---|---|"]
        lines += [f"| `{d.relative_to(root)}` | `{o.relative_to(root)}` |" for d, o in sorted(dups.items())]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


# ---------- commands ----------
def cmd_dedupe(a):
    project = Path(a.project)
    root = Path(a.footage) if a.footage else _footage_root(project)
    _, dups = find_duplicates(root)
    adir = project / "edit" / "assemble"
    save_json(adir / "dedupe.json", {str(d): str(o) for d, o in dups.items()})
    write_dedupe_report(adir / "dedupe_report.md", root, dups, "Duplicate footage")
    log(f"{len(dups)} byte-identical duplicates under {root} -> {adir / 'dedupe_report.md'}")
    for d, o in list(dups.items())[:20]:
        log(f"  skip {d.relative_to(root)}  ==  {o.relative_to(root)}")


def _footage_root(project: Path) -> Path:
    import re
    src = project / "edit" / "SOURCES.md"
    if src.exists():
        for line in src.read_text().splitlines():
            if line.lower().startswith("footage root"):
                m = re.search(r"(/\S+|[A-Za-z]:\\\S+)", line)
                if m and Path(m.group(1)).exists():
                    return Path(m.group(1))
    if (project / "sources" / "footage").exists():
        return project / "sources" / "footage"
    sys.exit("No footage root: pass --footage or write it in edit/SOURCES.md")


def _protect(path: Path) -> None:
    PROTECTED_LIST.parent.mkdir(parents=True, exist_ok=True)
    existing = PROTECTED_LIST.read_text().splitlines() if PROTECTED_LIST.exists() else []
    s = str(path.resolve())
    if s not in existing:
        with open(PROTECTED_LIST, "a") as f:
            f.write(s + "\n")


def cmd_workcopy(a):
    project = Path(a.project)
    src = Path(a.source).resolve()
    if not src.is_dir():
        sys.exit(f"source folder not found: {src}")
    work = Path(a.to).resolve() if a.to else src.parent / f"{src.name}_WORK"
    raw = work / "RAW_COPY"
    if src in raw.parents or raw == src:
        sys.exit("the WORK folder cannot be inside the source folder")
    files = media_files(src) if not a.all_files else sorted(p for p in src.rglob("*") if p.is_file() and not p.name.startswith("."))
    total = sum(p.stat().st_size for p in files)
    log(f"source {src}: {len(files)} files, {total / 1e9:.1f} GB")

    # 1. duplicates — skipped, never deleted
    _, dups = find_duplicates(src)
    skip_bytes = sum(d.stat().st_size for d in dups)
    log(f"byte-identical duplicates: {len(dups)} ({skip_bytes / 1e9:.1f} GB) — skipped")

    # 2. space check
    need = (total - skip_bytes) * 1.1 + 20e9  # copy + previews/exports headroom
    free = shutil.disk_usage(work.parent if work.parent.exists() else src.parent).free
    if free < need and not a.force:
        sys.exit(f"not enough free space on the drive: {free / 1e9:.0f} GB free, about {need / 1e9:.0f} GB needed "
                 f"(copy + 10% + 20 GB for previews/exports). Free space or pass --force.")

    for d in WORK_SUBDIRS:
        (work / d).mkdir(parents=True, exist_ok=True)
    logs = work / "logs"
    write_dedupe_report(logs / "dedupe_report.md", src, dups, "Duplicate footage (skipped from RAW_COPY)")

    # 3. copy + verify
    rows, mismatched, copied, skipped_existing = [], [], 0, 0
    for i, p in enumerate(files, 1):
        rel = p.relative_to(src)
        if p in dups:
            rows.append([str(p), "", p.stat().st_size, "", f"SKIPPED duplicate of {dups[p].relative_to(src)}"])
            continue
        dst = raw / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() and dst.stat().st_size == p.stat().st_size:
            skipped_existing += 1
        else:
            shutil.copy2(p, dst)
            copied += 1
        hs, hd = sha256(p), sha256(dst)
        ok = hs == hd
        if not ok:
            shutil.copy2(p, dst)
            hd = sha256(dst)
            ok = hs == hd
            if not ok:
                mismatched.append(str(rel))
        rows.append([str(p), str(dst), p.stat().st_size, hs, "OK" if ok else "MISMATCH"])
        if i % 50 == 0:
            log(f"  {i}/{len(files)} verified")
    with open(logs / "copy_manifest.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["source", "copy", "bytes", "sha256", "status"])
        w.writerows(rows)

    # 4. point the project at the copy; originals go on the protected list
    edit = project / "edit"
    edit.mkdir(parents=True, exist_ok=True)
    (edit / "SOURCES.md").write_text(
        f"Footage root (read-only): {raw}\n"
        f"Originals (never read again by Claude): {src}\n"
        f"Working copy made: {_dt.datetime.now().isoformat(timespec='seconds')}\n"
        f"Copy manifest: {logs / 'copy_manifest.csv'}\n"
        f"Duplicates skipped: {len(dups)} (see {logs / 'dedupe_report.md'})\n"
        f"Premiere project + scratch disks: {work / 'PROJECT'}\n"
        f"Cleaned WAVs: {work / 'AUDIO_CLEAN'}\n"
    )
    _protect(src)
    _protect(raw)
    save_json(project / "edit" / "assemble" / "workcopy.json",
              {"source": str(src), "work": str(work), "raw_copy": str(raw), "files": len(files), "copied": copied,
               "already_there": skipped_existing, "duplicates_skipped": len(dups), "mismatched": mismatched,
               "bytes": total - skip_bytes})
    log(f"RAW_COPY: {copied} copied, {skipped_existing} already there, {len(dups)} duplicates skipped, {len(mismatched)} MISMATCH")
    log(f"project now reads from {raw}; originals at {src} are on the protected list ({PROTECTED_LIST})")
    log(f"Premiere: save the project in {work / 'PROJECT'} and set File → Project Settings → Scratch Disks to that folder")
    if mismatched:
        sys.exit("some copies did not verify after two attempts: " + ", ".join(mismatched[:10]))


def cmd_handoff(a):
    project = Path(a.project)
    adir = project / "edit" / "assemble"
    wc = load_json(adir / "workcopy.json") if (adir / "workcopy.json").exists() else {}
    cull = load_json(adir / "cull.json") if (adir / "cull.json").exists() else []
    ranges = load_json(adir / "speech_ranges.json") if (adir / "speech_ranges.json").exists() else {}
    mcs = load_json(adir / "multicams.json") if (adir / "multicams.json").exists() else []
    cats = load_json(adir / "categories.json") if (adir / "categories.json").exists() else {}
    manifest = load_json(project / "edit" / "premiere" / "manifest.json") if (project / "edit" / "premiere" / "manifest.json").exists() else {}

    rejected = [c for c in cull if c.get("reject")]
    flagged: dict[str, int] = {}
    for c in cull:
        for w in c.get("warn") or []:
            if w in FLAG_REASONS:
                flagged[w] = flagged.get(w, 0) + 1
    speech_s = sum((r[1] - r[0]) for v in ranges.values() for r in (v.get("ranges") or []))
    removed_s = sum(v.get("removed_s", 0) for v in ranges.values())
    by_cat: dict[str, int] = {}
    for v in cats.values():
        by_cat[v] = by_cat.get(v, 0) + 1
    couple = a.title or project.name
    out = Path(a.out) if a.out else (Path(wc["work"]) / "EDITOR_START_HERE.md" if wc.get("work") else project / "EDITOR_START_HERE.md")

    L = [f"# {couple} — start here", "", f"Prepared by the Buwan engine, {_dt.datetime.now().strftime('%Y-%m-%d %H:%M')}. Nothing was deleted; everything below is additive.", ""]
    L += ["## Do these three things first", "",
          "1. Open **A-Roll clean** and listen through once. Mark the lines you want with markers — that is the story.",
          "2. Pick b-roll from the category bins: `05 Reactions & BTS` for bursts, `06 Establishing` for breathing room, `<category>/Steady picks` for the usable part of a shaky creative shot. `00 Flagged` is the last resort, not the first.",
          "3. Open **STABILIZE – Warp** once (Premiere) so Warp Stabilizer analyses in the background; in Final Cut tick **Stabilization** on the clips keyworded `stabilize`. Then cut in your own sequence.", ""]
    if wc:
        L += ["## Where the footage is", "",
              f"- Working copy: `{wc['raw_copy']}` — the project reads only from here.",
              f"- Originals: `{wc['source']}` — untouched, read-only, do not relink to them.",
              f"- Duplicates skipped: {wc.get('duplicates_skipped', 0)} byte-identical files (`logs/dedupe_report.md`). Copy verified by SHA-256 (`logs/copy_manifest.csv`).", ""]
    L += ["## What is in the bins", ""]
    for k in sorted(by_cat):
        L.append(f"- `{k}` — {by_cat[k]} clips")
    L += ["", "## Flagged, not rejected", "",
          f"- Rejected (unusable, in `00 Rejected (cull)`): {len(rejected)}"]
    for w, n in sorted(flagged.items()):
        L.append(f"- `00 Flagged/{FLAG_REASONS[w]}`: {n} clips — still usable if a key moment only exists there")
    L += ["", "## Speech", "",
          f"- {len(ranges)} speech clips, {speech_s / 60:.1f} min of speech kept, {removed_s / 60:.1f} min of dead air removed.",
          "- `01 Speech/Speech ranges` — one subclip per spoken stretch. `01 Speech/Clean audio` — levelled −17 LUFS WAVs to lay under the picture.",
          (f"- Multicam: {len(mcs)} SYNC sequences. Right-click each → **Multi-Camera → Enable** before cutting from it." if mcs else "- Multicam not synced (on request: `/buwan:multicam` — vows, interviews, ceremony)."), ""]
    sd = load_json(adir / "steady.json") if (adir / "steady.json").exists() else {}
    bc = sum(1 for v in sd.values() if v["decision"] == "best-cut"); wp = sum(1 for v in sd.values() if v["decision"] == "warp"); ts = sum(1 for v in sd.values() if v["decision"] == "too-shaky")
    L += ["## Shaky Creative/Glider footage", "",
          f"- {bc} clips have a steady cut (Steady picks), {wp} need Warp Stabilizer / Stabilization (STABILIZE – Warp), {ts} are too shaky (`00 Flagged/Heavy motion`). Details: `edit/steady_report.md`.",
          "- Shaky clips on the other cameras were left alone on purpose.", ""]
    L += ["## Sequences", "",
          "- **A-Roll clean** — every speech range back to back, a marker per source clip. Listen here, never in the raw bins.",
          "- **STABILIZE – Warp** — holding pen for the clips Warp Stabilizer should fix. Not a cut.",
          "- Your cutting sequence is yours to make: 1920×1080 · 23.976 · TC 01:00:00:00; dialogue −17 LUFS, peaks −6 dBFS, music bed −20 dB.", ""]
    if manifest.get("grade"):
        L.append(f"- Look chosen: **{manifest['grade']['look']}** ({manifest['grade'].get('intensity', 80)}%).")
    L += ["", "## Not done yet (on purpose)", "",
          "- No multicam sync, no story, no cut, no music placed. `/buwan:multicam` syncs by audio when you want it; `/buwan:plot` does the Story-Lock; `/buwan:sde` builds the music-driven cut after that.",
          "- No captions, no graphics, no export settings. Those are `/buwan:graphics`, `/buwan:sfx`, `/buwan:export`."]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n")
    log(f"wrote {out}")


FLAG_REASONS = {"heavy-motion": "Heavy motion", "soft-focus": "Soft focus", "dark": "Dark", "bright": "Blown exposure", "frozen": "Frozen"}
