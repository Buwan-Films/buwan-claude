---
name: grade
description: Pipeline stage 04, on request — the grade is not in the basics. Build the studio look from the studio's own film (a LUT matched to e.g. the last SDE) or use the studio LUTs (Warm, Cool, B&W), apply it in Premiere, Final Cut or Resolve on the enhanced clips (their exposure is already fixed), then measure it with the grade check. Use when an editor says grade, color, LUT, look, "apply the grade", color correct, or after audio polish. Also use to calibrate the studio look from reference stills.
argument-hint: "[warm|cool|bw] [project folder] | calibrate <stills folder> <look>"
---

# 04 Grade

Camera footage only — reels made from screen recordings and graphics skip the grade.

**The grade is its own step, run when the editor asks.** The basics (`/buwan:basics`) and the speech moments (`/buwan:multicam`) already fixed the exposure on every clip and baked no look in, so the grade stays fully editable in the app.

## 0. The studio look from the studio's film (once per reference)
`node "${CLAUDE_PLUGIN_ROOT}/scripts/assemble.js" look <project> --reference "<studio film, e.g. the last SDE>" [--name Buwan_Film]` → `edit/grade/Buwan_Film.cube` (33-point) + `edit/grade/Buwan_Film_preview.jpg` (before / after on this wedding's footage). Show the preview before applying. It matches the film's tone (soft film contrast, whites kept white) and its color by shadows / mids / highlights. Reuse the `.cube` on later weddings with the same reference; copy it into `kit/luts/` when the studio adopts it. Otherwise use the stock studio LUTs below.

## 1. Choose the look
One look per film: **Warm** (naturalistic, golden) or **Cool** (desaturated, blue-hour, rainy, modern venue), from the day's palette. **B&W** only for the most intimate beats (vows, letters, a parent's message). Ask the editor if the palette isn't obvious from thumbnails; say which you chose and why.

## 2. Apply (editor's app)
Engine shortcuts (same look on every camera clip, music and kit graphics skipped): Final Cut → rebuild the timeline with `assemble.js build … --grade <look> --fcp-lut` (experimental Custom LUT filter; the Buwan LUTs are installed in FCP's Custom LUT list by setup-kit, so the manual route is the same list). Resolve → **Workspace → Scripts → Edit → buwan_grade** with the timeline open (set `BUWAN_LUT` or edit `LUT_PATH` in the script; installed by setup-kit). Premiere → the LUT must be in Premiere's Creative look list (`/buwan:setup-kit` installs `kit/luts/*.cube`; copy a new `Buwan_Film.cube` to `~/Library/Application Support/Adobe/Common/LUTs/Creative/` and restart Premiere). Premiere 26.x won't let a script load a LUT, so the editor picks Lumetri → Creative → Look → the LUT once (on an adjustment layer per scene, or one clip), and the bridge copies it: `/buwan-premiere:premiere-apply grade` with `{look_from:"<sequence>/<index>"}`. Then balance per shot as below.
LUTs: `kit/luts/Buwan_Warm.cube`, `Buwan_Cool.cube`, `Buwan_BW.cube` (in the workspace after `/buwan:setup-kit`). Order is always: **camera Log→Rec.709 conversion (none for S-Cinetone) → balance (exposure — already fixed on the enhanced clips — white balance, match shots) → Buwan look LUT at 60–100% → final tweak**.
Baking the look into files instead (only when the editor asks, e.g. a quick delivery): `assemble.js render <project> --look edit/grade/Buwan_Film.cube` into a new folder.
- **Premiere:** one adjustment layer per scene. Lumetri on clips = Basic Correction (Input LUT = camera's Rec.709 LUT if Log, then WB/exposure). Lumetri on the adjustment layer = Creative → Look → Browse → Buwan LUT, Intensity 60–100.
- **Resolve:** Color page node tree `CST/Log→709 → Balance → Buwan LUT (Key Output Gain 0.6–1.0) → Final`. Put the LUT node in a shared node or Group Post-Clip so every shot gets the same one.
- **Final Cut:** on each clip, Custom LUT (camera LUT) → Color Wheels/Board for balance → Custom LUT (Buwan look, Mix 60–100%). Or put the look on an adjustment-layer title spanning the scene.
- Shot matching: skin tones first. The LUTs protect skin from desaturation; don't push saturation back up globally.

## 3. Measure
Export a graded H.264 proxy of the timeline (or stills of 8–12 key shots) to `edit/grade/`, then:
```
node "${CLAUDE_PLUGIN_ROOT}/scripts/grade-check.js" check edit/grade/<file> --look <warm|cool|bw>
```
It compares black level, highlight level, average brightness, saturation and hue to the studio targets (`kit/grade/targets.json` in the workspace, else the plugin's starting targets) and lists the timecodes of shots that drift. Report the table; fix FAIL shots and re-measure. B&W beats inside a color film: check them separately with `--look bw`.

## Calibrate the studio look (studio owner)
When the owner has a grade they love: export 8–12 stills of it (skin, wide, interior, night) into a folder, then
```
node "${CLAUDE_PLUGIN_ROOT}/scripts/grade-check.js" calibrate <stills folder> --look warm --targets kit/grade/targets.json
```
and commit the updated targets (and the exported .cube from Resolve: right-click node → Generate LUT → 33 Point Cube) to the plugin repo so every editor gets them.

Same-day mode: saved look applied by adjustment layer, one measurement pass on stills.
