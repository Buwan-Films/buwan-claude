---
name: wedding-day
description: The Buwan same-day run for Premiere Pro editors — Claude Code makes new ENHANCED clips from the raw footage into a new folder (exposure fixed on every clip; shaky Creative/Glider shots cut to their best part with a smooth glide; no grade), the raw files never touched, and stops. Interviews/vows/speeches (/buwan:multicam) and the grade (/buwan:grade) are separate skills the editor asks for. Use when a Premiere editor says "wedding day", "start the SDE", "run the basics", "enhance the clips", "new clips from the shooters", or drops a footage folder on the day.
argument-hint: "<YYYY-MM-DD>_<Couple> --footage <raw folder on the SSD>"
---

# Wedding day — Premiere Pro

Load `/buwan:house-rules` and `/buwan:basics`. `/buwan:basics` is the whole run; this skill adds the Premiere hand-off and the clock. Keep a running clock (ask for the screening time once) and report after every phase: done · time used · time left.

**Scope is the basics, then stop:** enhanced clips (exposure fixed, shaky Creative/Glider best cut + glide, no grade) into `<raw>_ENHANCED_<date-time>/`. No copy, no dedupe, no file organizing, no speech work, no grade, no sync, no story, no cut, no music, no sequence to cut in.

## Phase 0 — check, don't do
- The raw folder on the SSD, one subfolder per shooter (`1-Creative` / `Glider`, `2-Main`, `3-3rd Cam`, `4-Drone`, `Audio`). Read only.
- Space: about 0.6 GB per minute of footage next to the raw folder.

## Phase 1 — the basics (`/buwan:basics`, unattended)
`scan --footage` → `cull` → `steady` → `exposure` → `render`.

## Phase 2 — hand-off to Premiere
Tell the editor: **File → Import** (or Media Browser) the `<raw>_ENHANCED_<date-time>` folder into their project — the camera/card folders come in as bins. The exposure is already fixed and the shaky Creative clips already glide (no Warp Stabilizer needed). No look is on them yet. Importing through the bridge (`import_folder`) only when the editor asks.

Report a table (what · result · check by hand) and **stop**. Then remind the editor of the two skills they can call next:
- **Interviews, vows, speeches** — `/buwan:multicam`: they list each moment's clips; the angles come back synced on the best clean audio with the dead air cut, in `<raw>_SPEECH_<date-time>/INTERVIEWS|VOWS|SPEECHES/`. Premiere: select the angles → **Create Multi-Camera Source Sequence** → Synchronize Point: Timecode.
- **The grade** — `/buwan:grade`: the studio look (built from the studio's film) picked once in Lumetri and copied by the bridge.

## On request only
- **Story** — `/buwan:plot`. **Cut** — `/buwan:sde`.
- **Bins and labels in the project** — `/buwan-premiere:premiere-apply`.

## New clips from the shooters
Run the basics again on the same raw folder (a new ENHANCED folder), or with `render --out <earlier folder>` to add only what's new. Nothing already imported is touched.

## Rules on the day
- Never write into the raw folder. Never create a sequence for the editor to cut in; never touch their sequences.
- If the bridge is needed and fails twice, stop and say so; the enhanced folder is usable without it.
- Every phase ends with one line the editor can act on; no theory.
