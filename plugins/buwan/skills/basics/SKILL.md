---
name: basics
description: The Buwan same-day basics — what Claude Code does for a new wedding project and nothing more: new ENHANCED clips from the raw footage, into a new folder on every run, the raw files never touched — dead air out of interviews, letters, speeches and vows with cleaned −17 LUFS audio; the exposure fixed on every clip; the studio look matched to the studio's own film; shaky Creative/Glider shots cut to their best part with a smooth glide. No copying, no dedupe, no file organizing, no sync, no story, no cut, no music. Use when an editor says "basics", "enhance the clips", "prep the footage", "start the wedding project", "run it on the cards", or drops a footage folder for a wedding. Works for any editing app (the clips are HEVC 10-bit .mov).
argument-hint: "<YYYY-MM-DD>_<Couple> --footage <raw folder on the SSD> [--reference <studio film>]"
---

# The basics — enhanced clips, the raw untouched

Load `/buwan:house-rules`. The engine does the work (`node "${CLAUDE_PLUGIN_ROOT}/scripts/assemble.js" …`); you check the results and report.

**The rule:** the raw folder is only ever read. Every run writes new clips into a new folder next to it, `<raw>_ENHANCED_<YYYYMMDD-HHMM>/`, with the same camera/card folders and clip names (`.mov`). Nothing is copied, deduplicated, moved or reorganized.

**Scope — these four things, then stop:**

| # | What | Engine | What the editor gets |
|---|---|---|---|
| 1 | **Dead air + speech audio** — interviews, letters, speeches, vows | `enhance <project> --render` → `deadair <project>` | each speech clip cut down to its speech ranges (silences out, 20 ms fades at the joins), laid on the cleaned audio (high-pass, noise reduction scaled to the noise, voice EQ) and levelled to **−17 LUFS, peaks −6 dBFS**. A speech clip whose own audio is silent (lav or recorder elsewhere) is rendered whole and flagged |
| 2 | **Exposure on every clip** | `exposure <project>` | every camera clip measured (8-bit, keyframes); outside the look's brightness band (`kit/grade/targets.json`, Warm 55–150) it gets a gentle fix, at most ±1.5 EV, never clipping highlights; low-key shots (rings on black) left alone and listed. `edit/exposure_report.md` |
| 3 | **The studio look** | `look <project> --reference <studio film>` (once per reference; reuse the `.cube`) | a 33-point LUT that matches this wedding's footage to the studio's finished film: its tone (soft film contrast, lifted blacks, a soft shoulder that keeps whites white) and its color by shadows / mids / highlights. Check `edit/grade/<name>_preview.jpg` (before / after) before rendering |
| 4 | **Shaky Creative/Glider shots** | `steady <project> [--gimbal …]` | the best cut of each shaky clip on the Creative/Glider camera, then a smooth glide (vid.stab, two passes, a slight zoom to hide the moving edge). Other cameras are left alone |

Then `render <project>` writes every clip: exposure fix → look → HEVC 10-bit 4:2:0, 80 Mbps, Rec.709 tags, the original audio on non-speech clips. Speech and shaky clips render first so they can be checked while the rest finishes. `render_log.csv` in the folder says what was done to each clip.

**Not in scope — only when the editor asks:** multicam sync (`/buwan:multicam`), the story (`/buwan:plot`), the cut (`/buwan:rough-cut`, `/buwan:sde`), Premiere bins and labels (`/buwan-premiere:premiere-apply`), music, graphics, export.

## Run (unattended; ~1 h per 4 h of footage on Apple Silicon)
1. `scan <project> --footage "<raw folder>"` → `cull <project>` (unusable clips — black, false starts — are left out of the render and listed). No copy, no dedupe.
2. Find the speech: `/buwan:organize` step 1 on audio (speech-level loudness over long stretches = `01 Speech`), then **look at one frame per candidate**: a letter or vows read on camera, or an interview, is speech even when it sits among prep clips. Save `edit/assemble/categories.json`.
3. `enhance --render` → `deadair`. Report minutes of speech kept and dead air removed; name the speech clips with no usable audio of their own.
4. `steady` (ask which Creative cards were on the gimbal if the folders don't say) → `exposure`.
5. `look --reference "<studio film>"` the first time (the editor names the film, e.g. the studio's last SDE); show the preview sheet. Later runs reuse `edit/assemble/look.json`, or `render --look <.cube>`.
6. Test first: `render <project> --out <folder> --only speech --limit 2`, then `--only shaky --limit 2`, then `--only clip --limit 2`. Check: HEVC Main 10; speech duration = speech kept; speech −17 ±1 LUFS, peaks ≤ −6; a graded frame against its raw frame. Then `render <project>` for everything (a new folder; pass `--out` only to continue a run that stopped).
7. Report a table: what · result · check by hand. **Stop.**

## New clips from the shooters
Run the same skill again on the same raw folder: a new `<raw>_ENHANCED_<date-time>/` with every clip. To only add the new ones to an earlier run, pass that run's folder with `--out`; clips already rendered there are skipped.

## Needs
- ffmpeg with vid.stab: `~/.buwan/ffmpeg-vidstab/bin/ffmpeg` (`scripts/build-ffmpeg-vidstab.sh`, called by `/buwan:setup-kit`). Without it the shaky clips are cut to their best part but not stabilized, and the log says so.
- Disk: about 0.6 GB per minute of footage for the enhanced clips.

## Rules
- Never write into the raw folder (the hook blocks it). Outputs go to `<raw>_ENHANCED_*/` and `<project>/edit/`.
- Keep vows, letters and speeches verbatim: dead air is cut only between words, never inside them.
- The look comes from the studio's own film, never a stock LUT. B&W is not applied in the basics.
