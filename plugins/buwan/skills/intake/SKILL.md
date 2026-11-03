---
name: intake
description: Pipeline stage 01 — start a new Buwan project and bring footage in. Use when an editor says "new project", "new wedding/corporate project", "intake", or points at card dumps / a footage folder.
argument-hint: "<YYYY-MM-DD>_<client> <wedding|corporate> <footage path>"
---

# 01 Intake

Follow the house rules (`/buwan:house-rules`). Arguments: $ARGUMENTS

1. **Project folder.** Create `projects/<YYYY-MM-DD>_<client>_<wedding|corporate>/` with `sources/footage`, `sources/audio`, `edit/transcripts`, `captions`, `exports`. Ask for date, client or shoot type only if missing.
2. **Copy, never move.** Copy camera files to `sources/footage/` and recorder/lav WAVs to `sources/audio/`. Organize by segment (`prep`, `ceremony`, `reception`; corporate: `sessions`, `awards`, `crowd`) only when filenames, folders or creation dates make it clear; otherwise keep the card structure. Windows: `robocopy <src> <dst> /E /COPY:DAT /R:2 /W:2` (never `/MIR` or `/PURGE`). macOS: `rsync -a --ignore-existing`.
3. **Verify.** File count and total bytes match source vs copy, per folder. Spot-check with `ffprobe` that a sample of clips opens and report codec, resolution, frame rate. Flag mixed frame rates (23.976 vs 29.97/59.94) — they matter for the EDL.
4. **Lock.** Make `sources/` read-only. Windows: `attrib +R "<project>\sources\*" /S`. macOS: `chmod -R a-w "<project>/sources"`.
5. **Report** as a short table: segment · clips · duration · size · camera/codec · problems. List files you couldn't place.

If the editor says to reference footage in place, skip steps 2–4 and record the path in `edit/SOURCES.md`.

The editor must keep the original cards or a backup until delivery — say so once in the report.
