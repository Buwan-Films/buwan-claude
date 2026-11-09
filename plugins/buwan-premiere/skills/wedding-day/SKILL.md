---
name: wedding-day
description: The Buwan same-day run for Premiere Pro editors — Claude Code makes new ENHANCED clips from the raw footage into a new folder (dead air out of interviews, letters, speeches and vows with cleaned −17 LUFS audio; exposure fixed on every clip; the studio look matched to the studio's film; shaky Creative/Glider shots cut to their best part with a smooth glide), the raw files never touched, and stops. The editor imports the folder and cuts. Use when a Premiere editor says "wedding day", "start the SDE", "run the basics", "enhance the clips", "new clips from the shooters", or drops a footage folder on the day.
argument-hint: "<YYYY-MM-DD>_<Couple> --footage <raw folder on the SSD> [--reference <studio film>]"
---

# Wedding day — Premiere Pro

Load `/buwan:house-rules` and `/buwan:basics`. `/buwan:basics` is the whole run; this skill adds the Premiere hand-off and the clock. Keep a running clock (ask for the screening time once) and report after every phase: done · time used · time left.

**Scope is the basics, then stop:** enhanced clips (dead air + speech audio, exposure, the studio look, shaky Creative/Glider best cut + glide) into `<raw>_ENHANCED_<date-time>/`. No copy, no dedupe, no file organizing, no sync, no story, no cut, no music, no sequence to cut in.

## Phase 0 — check, don't do
- The raw folder on the SSD, one subfolder per shooter (`1-Main`, `2-Creative` / `Glider`, `3-Reactions`, `4-Drone`, `Audio`). Read only.
- The studio film to match for the look (the editor names it once; later runs reuse the LUT).
- Space: about 0.6 GB per minute of footage next to the raw folder.

## Phase 1 — the basics (`/buwan:basics`, unattended)
`scan --footage` → `cull` → speech found (audio, then one frame per candidate) → `enhance --render` → `deadair` → `steady` → `exposure` → `look` (first time) → test renders (2 speech, 2 shaky, 2 plain) → `render`.

## Phase 2 — hand-off to Premiere
Tell the editor: **File → Import** (or Media Browser) the `<raw>_ENHANCED_<date-time>` folder into their project — the camera/card folders come in as bins. The clips are already graded and leveled: no LUT, no Lumetri, no audio repair needed on them; Warp Stabilizer is not needed on the shaky Creative clips. Importing through the bridge (`import_folder`) only when the editor asks.

Report a table (what · result · check by hand) and **stop**.

## On request only
- **Multicam** — `/buwan:multicam` (vows, interviews, ceremony).
- **Story** — `/buwan:plot`.
- **Cut** — `/buwan:sde`.
- **Bins and labels in the project** — `/buwan-premiere:premiere-apply`.

## New clips from the shooters
Run the basics again on the same raw folder (a new ENHANCED folder), or with `render --out <earlier folder>` to add only what's new. Nothing already imported is touched.

## Rules on the day
- Never write into the raw folder. Never create a sequence for the editor to cut in; never touch their sequences.
- If the bridge is needed and fails twice, stop and say so; the enhanced folder is usable without it.
- Every phase ends with one line the editor can act on; no theory.
