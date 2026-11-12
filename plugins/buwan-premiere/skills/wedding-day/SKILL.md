---
name: wedding-day
description: The Buwan same-day run for Premiere Pro editors — Claude Code makes new ENHANCED clips from the raw footage into a new folder (exposure and white balance fixed on every clip; shaky Creative/Glider shots cut to their best part with a smooth glide; no grade), the raw files never touched, and stops. Interviews/vows/speeches (/buwan:multicam) and the grade (/buwan:grade) are separate skills the editor asks for. Use when a Premiere editor says "wedding day", "start the SDE", "run the basics", "enhance the clips", "new clips from the shooters", or drops a footage folder on the day.
argument-hint: "<YYYY-MM-DD>_<Couple> --footage <raw folder on the SSD>"
---

# Wedding day — Premiere Pro

Load `/buwan:house-rules` and `/buwan:basics`. `/buwan:basics` is the whole run; this skill adds the Premiere hand-off and the clock. Keep a running clock (ask for the screening time once) and report after every phase: done · time used · time left.

**Scope is the basics, then stop:** enhanced clips (exposure and white balance fixed, shaky Creative/Glider best cut + glide, no grade) into `<raw>_ENHANCED_<date-time>/`. No copy, no dedupe, no file organizing, no speech work, no grade, no sync, no story, no cut, no music, no sequence to cut in.

## Phase 0 — check, don't do
- The raw folder on the SSD, one subfolder per shooter (`1-Creative` / `Glider`, `2-Main`, `3-3rd Cam`, `4-Drone`, `Audio`). Read only.
- Space: about 0.6 GB per minute of footage next to the raw folder.

## Phase 1 — the basics (`/buwan:basics`, unattended)
`scan --footage` → `cull` → `steady` → `exposure` → `render`.

## Phase 2 — hand-off to Premiere
**One-command import** (the MCP Bridge panel open in the editor's project): `node <buwan>/scripts/assemble.js premiere-import <project>` → `edit/premiere/enhanced.json`, then the bridge step `enhanced` (`node <buwan-premiere>/scripts/premiere-snippet.js enhanced <project>/edit/premiere/enhanced.json` → `execute_extendscript`; repeat while `remaining > 0`). The clips land in **ENHANCED <date-time>/<camera>** bins; drone clips Teal, clips with speech Mango (once transcribed) with what they sound like and their first words in the **Description** column — type a word from the vows in the Project panel search to find the clip. No sequences are made.
Without the bridge: **File → Import** (or Media Browser) the `<raw>_ENHANCED_<date-time>` folder — the camera/card folders come in as bins.
The exposure is already fixed and the shaky Creative clips already glide (no Warp Stabilizer needed). No look is on them yet.

Report a table (what · result · check by hand) and **stop**. Then remind the editor of the two skills they can call next:
- **Interviews, vows, speeches** — `/buwan:multicam`: they list each moment's clips; the angles come back synced on the best clean audio with the dead air cut, in `<raw>_SPEECH_<date-time>/INTERVIEWS|VOWS|SPEECHES/`. Premiere: select the angles → **Create Multi-Camera Source Sequence** → Synchronize Point: Timecode.
- **The grade** — `/buwan:grade`: the studio look (built from the studio's film) picked once in Lumetri and copied by the bridge.

## On request only
- **Story** — `/buwan:plot`. **Cut** — `/buwan:sde`.
- **Bins and labels in the project** — `/buwan-premiere:premiere-apply`.

## New clips from the shooters
`/buwan:sync <project>` each time new cards land in the raw folders: only the new clips are checked, fixed and rendered, into the same `_ENHANCED_` folder, then **transcribes** every clip with speech not transcribed yet (local whisper, ~35× real time) into `edit/transcripts/`. Then `premiere-import` + bridge `enhanced` again: only the new files are imported, and clips whose transcript just arrived get their Mango label and Description. Nothing the editor moved, renamed or relabelled is touched.

## Rules on the day
- Never write into the raw folder. Never create a sequence for the editor to cut in; never touch their sequences.
- If the bridge is needed and fails twice, stop and say so; the enhanced folder is usable without it.
- Every phase ends with one line the editor can act on; no theory.
