---
name: basics
description: The Buwan same-day basics — what Claude Code does for a new wedding project and nothing more — dedupe (working copy on the SSD), cull, categorize, dead air, label colors, and shaky Creative/Glider footage (best cut, or Warp Stabilizer). No multicam sync, no story, no cut, no music. The editor made the project and placed the music by hand. Use when an editor says "basics", "prep the footage", "start the wedding project", "run it on the cards", or drops a footage folder for a wedding. Works for Premiere Pro (through the bridge) and Final Cut Pro (through the FCPXML).
argument-hint: "<YYYY-MM-DD>_<Couple> --footage <raw folder on the SSD> [--grade warm|cool|bw] [--new-clips]"
---

# The basics — the only goal for a new wedding project

Load `/buwan:house-rules`, then the editor's app playbook (`${user_config.nle}`: `/buwan:premiere` + `/buwan-premiere:premiere-apply`, or `/buwan:final-cut`). The engine does the work (`node "${CLAUDE_PLUGIN_ROOT}/scripts/assemble.js" …`); you make the category calls and report.

**Scope — do these six things and stop:**

| # | Step | Engine | What the editor gets |
|---|---|---|---|
| 1 | **Dedupe + working copy** | `workcopy <project> --source <raw folder>` | `<raw>_WORK/RAW_COPY/` on the same SSD, verified by SHA-256, byte-identical duplicates skipped (`logs/dedupe_report.md`); originals never read again |
| 2 | **Cull** | `scan <project>` → `cull <project>` | unusable clips rejected (false start, black, blown, dead) — flags, never deletions |
| 3 | **Categorize** | `/buwan:organize` steps 1–2 → `edit/assemble/categories.json` | every clip in one of the 12 studio categories (same-day: from folder names + audio, no thumbnails) |
| 4 | **Dead air** | `enhance <project> --render` → `deadair <project>` | speech ranges with the silence cut out; cleaned −17 LUFS WAVs in `AUDIO_CLEAN/`; the **A-Roll clean** to listen through |
| 5 | **Label colors** | Premiere: bridge `organize` · Final Cut: `organize <project>` FCPXML (roles) | the house colors per category; rejects in `00 Rejected (cull)`; soft / dark / blown / frozen b-roll in `00 Flagged/<reason>` |
| 6 | **Shaky — Creative/Glider only** | `steady <project>` | for every shaky clip on the creative/glider camera: the **best steady cut** (≥2.5 s) as a Steady pick, or **Warp Stabilizer** when there is no steady stretch, or it stays in Flagged when nothing can save it. Shaky clips on other cameras are left alone — a shaky reaction is still a reaction |

**Not in scope — only when the editor asks:** multicam sync (`/buwan:multicam`), the story (`/buwan:plot`), the cut (`/buwan:rough-cut` / `assemble.js build`), music, graphics, grade, export. Never start any of them on your own, and never create a cutting sequence.

## What the editor did first (check, don't do)
- Made the project by hand: Premiere `<WORK>/PROJECT/<Couple>_SDE.prproj` with **File → Project Settings → Scratch Disks** on `PROJECT/` (and Window → Extensions → MCP Bridge running); Final Cut: a library on the SSD next to `<WORK>/`.
- Put the music where they want it. The engine does not touch music in this run.
- Pointed you at the raw clips folder: one subfolder per shooter (`1-Main`, `2-Creative` or `Glider`, `3-Reactions`, `4-Drone`, `Audio`). Shooters add clips to their own folder as the day goes.

## Run (unattended, ~15–25 min per 300 clips)
1. `workcopy` (step 1). If the SSD is short on space the engine stops and says so → `/buwan:intake --in-place` and `scan --dedupe` instead.
2. `scan` → `cull` → show the rejected list with reasons.
3. Categories → `categories.json`. On an SDE, no thumbnails: folder name first, then audio (speech-level loudness over long stretches = `01 Speech`).
4. `enhance --render` → `deadair`. Report minutes of speech kept and dead air removed; name the clips under 15 dB SNR (use the recorder file).
5. `steady`. Report: best cuts · warp · too shaky.
6. Apply in the app:
   - **Premiere:** `premiere <project> --grade <look>` → bridge `basics` (= `import` → `organize` → `deadair` → `aroll` → `steady`). Result: category bins with labels, `00 Rejected (cull)`, `00 Flagged/<reason>`, `01 Speech/Speech ranges` subclips, `01 Speech/Clean audio`, the **A-Roll clean** sequence, `<category>/Steady picks` subclips, and a **STABILIZE – Warp** sequence holding the clips that need Warp Stabilizer (effect applied; open it once so Premiere analyses).
   - **Final Cut:** `organize <project> --event "<Couple>"` → `edit/organize_vN.fcpxml` (keywords = bins, roles = colors, rejects as Rejected, warnings as notes, speech ranges as Favorites named `speech`, steady picks as Favorites named `steady` + keyword `steady pick`, clips for stabilizing with keyword `stabilize` and a note). Then `aroll <project> --event "<Couple>"` → `edit/aroll-clean_vN.fcpxml`. Editor imports both (**File → Import → XML**), sets the role colors once (**Modify → Edit Roles**), ticks **Stabilization** in the Inspector on the `stabilize` clips.
7. `handoff <project> --title "<Couple>"` → `<WORK>/EDITOR_START_HERE.md`.
8. Report a table: step · result · check by hand. **Stop.**

## New clips from the shooters (`--new-clips`)
Same folders, more files: `workcopy` again (copies only the new, skips duplicates of anything already copied) → `scan` → `cull` → categories for the new paths → `enhance --render` → `deadair` → `steady` → apply (Premiere `status` → `import` → `organize` → `deadair` → `steady`; Final Cut: a new `organize_vN.fcpxml`, import adds only what is new) → `handoff`. Nothing already in the project is touched.

## Rules
- Never write into the raw folder or `RAW_COPY/` (the hook blocks it). Outputs go to `<project>/edit/`, `AUDIO_CLEAN/`, `PROJECT/`.
- Rejects and flags are never deletions; the editor can un-reject by name (`cull.json`, `reject: []`).
- One line the editor can act on at the end of every step; no theory.
