---
name: wedding-day
description: The Buwan same-day run for Premiere Pro editors — the editor has made the project and placed the music by hand; Claude Code then does only the basics in the open project — dedupe (working copy on the SSD), cull, categorize, dead air + A-Roll clean, label colors, and shaky Creative/Glider footage (best cut or Warp Stabilizer) — and stops. Multicam sync, the story and the cut are separate skills the editor asks for. Use when a Premiere editor says "wedding day", "start the SDE", "run the basics", "new clips from the shooters", or drops a footage folder on the day.
argument-hint: "<YYYY-MM-DD>_<Couple> --footage <raw folder on the SSD> [--grade warm|cool|bw] [--new-clips]"
---

# Wedding day — Premiere Pro

Load `/buwan:house-rules`, `/buwan:basics` and `/buwan-premiere:premiere-apply` first. This skill is the Premiere order of operations and the reporting; the engine and the bridge do the work. Keep a running clock (ask for the screening time once) and report after every phase: done · time used · time left.

**Scope is the basics, then stop.** Six things: dedupe, cull, categorize, dead air, label colors, shaky Creative/Glider. Nothing else unless the editor asks — not sync (`/buwan:multicam`), not the story (`/buwan:plot`), not the cut, not music, not a sequence to cut in.

## Phase 0 — what the editor has already done (check, don't do)
- Footage folder on the SSD: one subfolder per shooter (`1-Main`, `2-Creative` / `Glider`, `3-Reactions`, `4-Drone`, `Audio`). Shooters drop clips into their own folder as the day goes.
- A new Premiere project saved as `<raw folder>_WORK/PROJECT/<Couple>_SDE.prproj` (the engine makes `<raw>_WORK/` in Phase 1 step 1 — if it isn't there yet, tell the editor where to save once it is), **File → Project Settings → Scratch Disks** all on `PROJECT/`, **Window → Extensions → MCP Bridge** running. "Verify Premiere connection"; if it fails twice, stop and say so.
- The music, wherever they want it. Not touched in this run.
- Grade look, if they want the LUT tagged in the manifest for later (Warm default). Nothing is graded in this run.

## Phase 1 — the basics (first batch of clips; ~15–25 min per 300 clips, unattended)
Engine, in order (`node <buwan>/scripts/assemble.js …`):
1. `workcopy <project> --source "<raw folder>"` — `RAW_COPY/` on the same SSD, verified by hash, **byte-identical duplicates skipped** and logged (a card copied twice or a `z/` backup never imports twice). From here only `RAW_COPY/` is read. Short on space → `/buwan:intake --in-place` + `scan --dedupe`.
2. `scan <project>` → `cull <project>` → show the rejected list with reasons.
3. Categories: `/buwan:organize` steps 1–2 → `edit/assemble/categories.json`. Same-day: folder names + audio, no thumbnails.
4. `enhance <project> --render` → `deadair <project>`. Report minutes of speech, minutes of dead air removed, clips under 15 dB SNR.
5. `steady <project>` — shaky clips on the Creative/Glider camera only: best steady cut (≥2.5 s) · Warp Stabilizer · too shaky. Other cameras untouched.
6. `premiere <project> [--grade <look>]` → `edit/premiere/manifest.json`.

Bridge (`premiere-snippet.js basics <manifest>` → `execute_extendscript`, or step by step: `import` until `remaining` is 0 → `organize` → `deadair` → `aroll` → `steady`).

Result the editor opens:
- category bins with the **house label colors**; `00 Rejected (cull)` for the unusable; `00 Flagged/Soft focus · Dark · Blown exposure · Frozen` for b-roll that shouldn't be a first pick (label kept, reason in Description);
- `01 Speech/Speech ranges` subclips with the dead air gone; `01 Speech/Clean audio` WAVs; the **A-Roll clean** sequence — the whole day's speech back to back, no duplicates;
- `<category>/Steady picks` — the best steady cut of each shaky Creative/Glider clip as a subclip; **STABILIZE – Warp** — the clips with no steady stretch, placed with Warp Stabilizer applied (open it once so Premiere analyses in the background; copy a stabilized clip from there into the cut); the rest in `00 Flagged/Heavy motion`.

Then `assemble.js handoff <project> --title "<Couple>"` → `<WORK>/EDITOR_START_HERE.md`. Report a table (step · result · check by hand) and **stop**.

## On request only
- **Multicam** — `/buwan:multicam` (vows, interviews, ceremony): `sync` → bridge `sync` → SYNC sequences the editor enables.
- **Story** — `/buwan:plot` on the A-Roll clean.
- **Cut** — `assemble.js build` → bridge `build` → `grade` → `enhance` (the full SDE flow, `/buwan:sde`).

## New clips from the shooters (`--new-clips`)
Same folders, more files: `workcopy` again (copies only the new, skips duplicates of anything already copied) → `scan` → `cull` → categories for the new paths → `enhance --render` → `deadair` → `steady` → `premiere …` → bridge `status` → `import` → `organize` → `deadair` → `steady` → `handoff`. Nothing already in the project is touched.

## Rules on the day
- Never write into the raw folder or `RAW_COPY/`. Never create a sequence for the editor to cut in; never touch their sequences.
- If a bridge step fails twice, fall back and say so: the organize/aroll FCPXML routes through Resolve (File → Import → Timeline, then File → Export → FCP 7 XML) into Premiere.
- Every phase ends with one line the editor can act on; no theory.
