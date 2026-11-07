---
name: wedding-day
description: The Buwan same-day-edit run for Premiere Pro editors, start to finish — footage + two music tracks in, an organized, colored, culled, synced, sound-cleaned Premiere project out, then (after Story-Lock) the music-driven SDE Cut graded and leveled in the open project. Use when a Premiere editor says "wedding day", "start the SDE", "new clips from the shooters", "run the basics", or drops a footage folder + music on the day.
argument-hint: "<project folder or client name> [--footage <dir>] [--music <dir>] [--grade warm|cool|bw] [--new-clips]"
---

# Wedding day — Premiere Pro

Load `/buwan:house-rules`, `/buwan:assemble` and `/buwan-premiere:premiere-apply` first. This skill is the order of operations and the reporting; the engine and the bridge do the work. Keep a running clock (ask for the screening time once) and report after every phase: done · time used · time left.

## Phase 0 — before the footage arrives (5 min)
- Project: `/buwan:intake <YYYY-MM-DD>_<Couple> wedding <footage folder>` in **reference-in-place** mode (no copying on an SDE; `edit/SOURCES.md` records the folder). Footage folder layout: one subfolder per shooter/camera (`1-Main`, `2-Creative`, `3-Reactions`, `4-Drone`, `Audio` for the recorder). Shooters drop their cards' clips into their own folder as the day goes.
- Music: `music/01_intro.<wav|mp3>` (the hook — no speech over it) and `music/02_story.<wav|mp3>` (the story through the outro), downloaded from Artlist and saved next to the footage. If the editor dragged the tracks in from the **Artlist Library** panel in Premiere (Window → Extensions → Artlist Library) instead, find them through the bridge (`search_project_items` / `get_project_items`, the two newest audio items; read each `getMediaPath()`), copy the files to `<project>/music/01_intro.<ext>` and `02_story.<ext>` (ask which is which if the names don't say), and continue. The engine reads the peak of track 2 and puts the kiss there, so pick track 2 for its build and peak, not just its mood.
- Premiere: new project saved as `<project>/edit/<Couple>_v1.prproj`, Window → Extensions → MCP Bridge running. "Verify Premiere connection".
- Grade: ask which studio look — Warm (default for Philippine daylight/garden weddings), Cool (hotel/ballroom, overcast), BW only for a highlight.

## Phase 1 — the basics (first batch of clips; ~15–25 min per 300 clips, unattended)
Engine, in order (`node <buwan>/scripts/assemble.js …`):
1. `scan <project> --footage <dir> --music <music dir>`
2. `cull <project>` → show the rejected list with reasons.
3. `music <project> --intro music/01_* --main music/02_*` → tell the editor the tempo and where the peak is.
4. `sync <project> --anchor "<the camera that rolled longest on the ceremony>" --trusted <cameras with correct clocks>` → cameras synced by sound, multicam groups.
5. Categories: `/buwan:organize` steps 1–2 → `edit/assemble/categories.json` (speech, prep, portraits, ceremony, reactions, establishing, reception, drone, music). On an SDE: from folder names + audio, no thumbnails.
6. `enhance <project> --render` and `deadair <project>`.
7. `premiere <project> --grade <look> --use-clean` → `edit/premiere/manifest.json`.

Bridge (`premiere-snippet.js <step> <manifest>` → `execute_extendscript`): `import` (repeat until `remaining` is 0) → `organize` → `deadair` → `aroll` → `sync`.
Result the editor opens: category bins with house label colors, `00 Rejected (cull)`, `01 Speech/Speech ranges` subclips with the dead air gone, `01 Speech/Clean audio` WAVs, the **A-Roll clean** sequence to listen through, one **SYNC** sequence per multicam group (editor enables Multi-Camera on each). Report: clips in/rejected/synced, minutes of speech, minutes of dead air removed, noisy clips to replace with the recorder file.

## Phase 2 — Story-Lock (editor + Claude, 20–40 min)
`/buwan:plot` on the speech (transcribe from the speech ranges; vows, letters, messages; Taglish verbatim). The editor approves the paper edit → `edit/assemble/selects.json`. This is the one creative gate that needs a person before the cut exists.

## Phase 3 — the cut (10 min, unattended)
1. `build <project> --selects edit/assemble/selects.json --multicam --name "SDE Cut" --grade <look> --options '{"title_at":"end","final_hold_s":27}'` → `.plan.json`, `.edl`, `.map.png`.
2. `/buwan:proof-gate edit/sde-cut_vN.edl --mode sde` — must pass or get a one-line override.
3. `premiere <project> --grade <look> --use-clean --plan edit/sde-cut_vN.plan.json` → bridge `build` → `grade` → `enhance` (both with `{sequence:"SDE Cut"}`).
Show the edit map and say in three lines what the shape is (cold open, where the peaks are, what's held, where the kiss sits).

## Phase 4 — the editor's part (creative only)
Watch-down in the SDE Cut sequence · swap b-roll where a shot is wrong for the line · nudge holds · speed ramps · kit graphics on the orange markers (`/buwan:graphics`: 07.07 title plate at the end, 06.02 logo reveal) · `/buwan:sfx` (riser into the title, hit on the logo) · `/buwan:review` · `/buwan:export` (venue master 1920×1080 H.264 20 Mbps, −17 LUFS, plus a USB copy).

## New clips from the shooters (any time, `--new-clips`)
Same folders, more files. Run: `scan` → `cull` → `sync` (same anchor) → categories for the new paths only → `enhance --render` → `deadair` → `premiere …` → bridge `status` → `import` → `organize` → `deadair`. Nothing already in the project is touched. If the new clips change the story (a late letter, the reception speeches), redo Phase 2–3 into **SDE Cut v2**; the editor's v1 stays.

## Rules on the day
- Never write into the footage folders. Never edit the editor's working sequence in place; new versions get new sequences.
- If a bridge step fails twice, fall back and say so: the picture cut imports as the EDL (`edit/sde-cut_vN.edl`, File → Import, 23.976, relink to the footage folder), or route the FCPXML through Resolve (File → Import → Timeline, then File → Export → FCP 7 XML) into Premiere.
- Every phase ends with one line the editor can act on; no theory.
