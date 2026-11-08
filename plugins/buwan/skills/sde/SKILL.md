---
name: sde
description: Same-day edit (SDE) / event-close sizzle mode — runs the whole Buwan pipeline compressed for a same-day deadline (gates still apply, rounds don't). Use when an editor says SDE, same-day edit, same day, sizzle, or "for the reception tonight".
argument-hint: "[project folder] [deadline time] [target length]"
---

# Same-day mode

Gates still apply, rounds don't. Saved look, minimal captions, one converge pass. Keep a running clock: ask for the deadline (e.g. "screening at 9:30 PM") and target length (usually 3–5 min), then plan backwards and show the time budget per stage.

| Stage | Same-day version |
|---|---|
| 01 Intake | `/buwan:intake … --work-copy` — a verified working copy next to the raw folder on the SSD (`<raw>_WORK/RAW_COPY/`), byte-identical duplicates skipped, originals never read again. No room → `--in-place` with `scan --dedupe`. Ask for the two music tracks (01 intro, 02 story). |
| Prep — **the basics** | `/buwan:basics`: dedupe (working copy) → cull → categorize → dead air + A-Roll clean → label colors → shaky Creative/Glider (best cut / Warp Stabilizer). Premiere through the bridge (`basics`), Final Cut through the organize + aroll FCPXML. **The editor made the project and placed the music; the run stops here.** Multicam only on request: `/buwan:multicam`. |
| 02 Story-Lock | `/buwan:plot` same-day mode: one pass, letters/vows/messages only; write `selects.json`. |
| 02 Rough cut | `/buwan:assemble` step 8: `assemble.js build … --name "SDE Cut" --grade <look> --options '{"title_at":"end","final_hold_s":27}'`. Read the edit map: cold open, letter first, two peaks, vow held, kiss on peak 2, one 25–30 s final hold, title last (house rules → "The SDE shape"). |
| Gate | `/buwan:proof-gate <edl> --mode sde` — must pass (or a one-line override). |
| 03 Audio | Auto-match to −17 LUFS + limiter −6 dBFS, one measurement. |
| 04 Grade | Saved look (Warm or Cool) on an adjustment layer, grade check on 6 stills. |
| 05 Graphics | SDE title plate (07.07) + end card (06.02/06.07) only; captions only where speech is unclear. One converge pass. |
| 06 SFX | Riser into the title, hit on the logo. |
| 07 Review | One watch-down with the editor. |
| 08 Export | H.264 master for the venue screen: 1920×1080, 23.976, 20 Mbps, −17 LUFS (check the venue's playback device), plus a backup copy on a second drive/USB. |

At every stage report: done, time used, time left. If the clock is short, cut scope (fewer beats, shorter film) — never skip a gate.
