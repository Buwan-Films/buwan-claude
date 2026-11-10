---
name: basics
description: The Buwan same-day basics — what Claude Code does for a new wedding project and nothing more: new ENHANCED clips from the raw footage, into a new folder on every run, the raw files never touched — the exposure fixed on every clip, shaky Creative/Glider shots cut to their best part with a smooth glide, no grade. No copying, no dedupe, no file organizing, no speech work, no grade, no sync, no story, no cut, no music. Use when an editor says "basics", "enhance the clips", "fix the exposure", "prep the footage", "start the wedding project", "run it on the cards", or drops a footage folder for a wedding. Works for any editing app (the clips are HEVC 10-bit .mov).
argument-hint: "<YYYY-MM-DD>_<Couple> --footage <raw folder on the SSD>"
---

# The basics — enhanced clips, the raw untouched

Load `/buwan:house-rules`. The engine does the work (`node "${CLAUDE_PLUGIN_ROOT}/scripts/assemble.js" …`); you check the results and report.

**The rule:** the raw folder is only ever read. Every run writes new clips into a new folder next to it, `<raw>_ENHANCED_<YYYYMMDD-HHMM>/`, with the same camera/card folders and clip names (`.mov`). Nothing is copied, deduplicated, moved or reorganized.

**Scope — two things, then stop:**

| # | What | Engine | What the editor gets |
|---|---|---|---|
| 1 | **Exposure on every clip** | `exposure <project>` | every camera clip measured (8-bit, keyframes); outside the studio brightness band (`kit/grade/targets.json`, 55–150) it gets a gentle fix, at most ±1.5 EV, never clipping highlights; low-key shots (rings on black) left alone and listed. `edit/exposure_report.md` |
| 2 | **Shaky Creative/Glider shots** | `steady <project> [--gimbal …]` | the best cut of each shaky clip on the Creative/Glider camera, then a smooth glide (vid.stab, two passes, a slight zoom to hide the moving edge). Other cameras are left alone |

Then `render <project>` writes every clip: exposure fix → HEVC 10-bit 4:2:0, 80 Mbps, Rec.709 tags, the original audio. **No grade** — the look is applied in the editing app with `/buwan:grade`. Shaky clips render first so they can be checked while the rest finishes. `render_log.csv` in the folder says what was done to each clip.

Interviews, letters, speeches and vows go through like every other clip (exposure fixed, original audio, full length). Merging their angles, the best audio and the dead air are `/buwan:multicam`, run by the editor.

**Not in scope — only when the editor asks:** interviews / vows / speeches (`/buwan:multicam`), the grade (`/buwan:grade`), the story (`/buwan:plot`), the cut (`/buwan:rough-cut`, `/buwan:sde`), Premiere bins and labels (`/buwan-premiere:premiere-apply`), music, graphics, export.

## Run (unattended; ~1 h per 5 h of footage on Apple Silicon)
1. `scan <project> --footage "<raw folder>"` → `cull <project>` (unusable clips — black, false starts — are left out of the render and listed). No copy, no dedupe.
2. `steady <project>` (ask which Creative cards were on the gimbal if the folders don't say).
3. `exposure <project>`.
4. `render <project>` for everything, straight away (a new folder; pass `--out` only to continue a run that stopped). Shaky clips come out first: spot-check one while the rest renders. A short test (`--only shaky|clip --limit 2 --out <folder>`) only after an engine update or with a new camera.
5. Report a table: what · result · check by hand. **Stop.**

## New clips from the shooters
The wedding is still going and new cards keep coming: `/buwan:sync <project>` — only the new clips are checked, fixed and rendered, into the same `_ENHANCED_` folder (the clips already there are skipped). Run it as often as cards arrive.

## Needs
- ffmpeg with vid.stab: `~/.buwan/ffmpeg-vidstab/bin/ffmpeg` (`scripts/build-ffmpeg-vidstab.sh`, called by `/buwan:setup-kit`). Without it the shaky clips are cut to their best part but not stabilized, and the log says so.
- Disk: about 0.6 GB per minute of footage for the enhanced clips.
- Footage in a Rec.709-ready profile (S-Cinetone on 10-bit bodies, see the house rules). The basics have no Log→709 step.

## Rules
- Never write into the raw folder (the hook blocks it). Outputs go to `<raw>_ENHANCED_*/` and `<project>/edit/`.
- No grade in the basics; `render --look <.cube>` bakes a look in only when the editor asks for it.
