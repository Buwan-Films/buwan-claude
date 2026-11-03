---
name: grade
description: Pipeline stage 04 — grade camera footage to the Buwan look with the studio LUTs (Warm, Cool, B&W), the same way in Premiere, Final Cut and Resolve, then measure it with the grade check. Use when an editor says grade, color, LUT, look, color correct, or after audio polish. Also use to calibrate the studio look from reference stills.
argument-hint: "[warm|cool|bw] [project folder] | calibrate <stills folder> <look>"
---

# 04 Grade

Camera footage only — reels made from screen recordings and graphics skip the grade.

## 1. Choose the look
One look per film: **Warm** (naturalistic, golden) or **Cool** (desaturated, blue-hour, rainy, modern venue), from the day's palette. **B&W** only for the most intimate beats (vows, letters, a parent's message). Ask the editor if the palette isn't obvious from thumbnails; say which you chose and why.

## 2. Apply (editor's app)
LUTs: `kit/luts/Buwan_Warm.cube`, `Buwan_Cool.cube`, `Buwan_BW.cube` (in the workspace after `/buwan:setup-kit`). Order is always: **camera Log→Rec.709 conversion → balance (exposure, white balance, match shots) → Buwan look LUT at 60–100% → final tweak**.
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
