---
name: intake
description: Pipeline stage 01 — start a new Buwan project and bring footage in. Use when an editor says "new project", "new wedding/corporate project", "intake", "working copy", "copy the cards to the SSD", or points at card dumps / a footage folder.
argument-hint: "<YYYY-MM-DD>_<client> <wedding|corporate> <footage path> [--work-copy | --copy | --in-place]"
---

# 01 Intake

Follow the house rules (`/buwan:house-rules`). Arguments: $ARGUMENTS

Three ways in. Pick by what the editor said; if they said nothing, **working copy** for a same-day edit on a Premiere machine, **copy** for everything else.

| Mode | When | Where the footage ends up |
|---|---|---|
| **Working copy on the drive** (`--work-copy`, SDE default) | the raw clips sit on an external SSD and the editor cuts off that SSD today | `<raw folder>_WORK/RAW_COPY/` next to the raw folder, on the same drive; the project reads only from the copy |
| **Copy into the workspace** (`--copy`) | highlight / full feature; the workspace drive has room | `projects/<…>/sources/footage` and `sources/audio` |
| **Reference in place** (`--in-place`) | no room to copy, or the editor says so | the cards themselves, recorded in `edit/SOURCES.md` |

In every mode the originals are never written to again, and the editor keeps the cards or a backup until delivery — say so once in the report.

## 1. Project folder (all modes)
Create `projects/<YYYY-MM-DD>_<client>_<wedding|corporate>/` with `edit/transcripts`, `captions`, `exports` (and `sources/footage`, `sources/audio` in copy mode). Ask for date, client or shoot type only if missing.

## 2a. Working copy on the drive
```
node "${CLAUDE_PLUGIN_ROOT}/scripts/assemble.js" workcopy <project> --source "<raw clips folder on the SSD>" [--to "<WORK folder>"]
```
The engine:
- checks free space first (copy + 10 % + 20 GB for previews/exports) and stops if it is short;
- finds **byte-identical duplicates** (same bytes under two paths — a card copied twice, a `z/` backup folder) and skips them, logging each one against its original in `logs/dedupe_report.md`. Nothing is deleted;
- copies everything else into `<WORK>/RAW_COPY/` with the folder structure and filenames unchanged, then verifies **every file by SHA-256** against its source (`logs/copy_manifest.csv`, re-copies a mismatch once);
- makes `<WORK>/PROJECT/` (the `.prproj` and all scratch), `AUDIO_CLEAN/`, `EXPORTS/`, `logs/`;
- writes `edit/SOURCES.md` with the footage root = `RAW_COPY/` and the originals path, and adds both to `~/.buwan/protected-paths.txt` so the source-protection hook refuses any write, move or delete there.
From this point on, never read the original folder again. Every later step (`scan`, `cull`, import) runs against `RAW_COPY/`.

Tell the editor once: save the Premiere project in `PROJECT/` and set **File → Project Settings → Scratch Disks** to `PROJECT/` before the first render, or previews land on the system drive. If they also want protection against the SSD itself failing, mirror `RAW_COPY/` to a second drive with the same command (`--source <WORK>/RAW_COPY --to <second drive>/<name>_MIRROR`).

## 2b. Copy into the workspace
Copy camera files to `sources/footage/` and recorder/lav WAVs to `sources/audio/`. Organize by segment (`prep`, `ceremony`, `reception`; corporate: `sessions`, `awards`, `crowd`) only when filenames, folders or creation dates make it clear; otherwise keep the card structure. Windows: `robocopy <src> <dst> /E /COPY:DAT /R:2 /W:2` (never `/MIR` or `/PURGE`). macOS: `rsync -a --ignore-existing`. Then verify (file count and bytes per folder, `ffprobe` a sample for codec / resolution / frame rate; flag mixed frame rates) and lock: Windows `attrib +R "<project>\sources\*" /S`, macOS `chmod -R a-w "<project>/sources"`.

## 2c. Reference in place
Record the folder in `edit/SOURCES.md` and run `assemble.js scan <project> --footage <dir> --dedupe` later so byte-identical duplicates stay out of the project (they otherwise import twice and play the same speech twice in the A-Roll clean).

## 3. Report
A short table: segment/camera · clips · duration · size · codec · problems — plus, in working-copy mode, copied / already there / duplicates skipped / mismatches, and the two paths (copy, originals). List files you couldn't place.
