# Maintaining the Buwan rules (studio owner)

The rules live in this repository. The claude.ai artifacts are the visual versions for people.

## Where each rule lives
| Change | Edit |
|---|---|
| Brand, beats, pacing targets, audio specs, deliverables, kit index | `plugins/buwan/skills/house-rules/SKILL.md` |
| Pacing numbers the gate measures | `plugins/buwan/scripts/proof-gate.js` (keep in sync with house-rules) |
| Stage steps | `plugins/buwan/skills/<stage>/SKILL.md` (intake, organize, plot, rough-cut, proof-gate, audio, grade, graphics, sfx, review, export, clipper, sde) |
| App steps | `plugins/buwan/skills/{premiere,final-cut,resolve}/SKILL.md` |
| What's protected | `plugins/buwan/scripts/protect-sources.js` (`sources/`, `RAW_COPY/`, and every path in `~/.buwan/protected-paths.txt`, which `assemble.js workcopy` fills) |
| Working copy, duplicates, hand-off note | `plugins/buwan/assemble/workcopy.py` (`workcopy`, `dedupe`, `handoff`); flagged-bin reasons in `assemble/premiere.py` (`FLAG_REASONS`) |
| Shaky creative footage (which cameras count, steady thresholds) | `plugins/buwan/assemble/steady.py` (`CREATIVE_CAMERAS`, `STEADY_MAX`, `WARP_MAX_MEAN`, `MIN_STEADY_S`); Premiere side in `buwan.jsx` (`stepSteady`) |
| The basics scope (what runs on a new project) | `plugins/buwan/skills/basics/SKILL.md`, `buwan-premiere/skills/wedding-day/SKILL.md`, bridge step `basics` in `buwan.jsx` |
| Per-app pipeline pages | `plugins/buwan/reference/pipeline-premiere.html`, `pipeline-final-cut.html` — edit the artifact, save the page here |
| Rule card every session starts with | `plugins/buwan/scripts/session-start.js` |
| Clip categories, bins, colors | `house-rules/SKILL.md` → "Clip categories, bins and colors" (and `skills/organize`) |
| Studio looks | `plugins/buwan/kit/luts/*.cube` — replace with LUTs exported from your reference grade (Resolve: right-click node → Generate LUT → 33 Point Cube). `tools/make-luts.py` regenerates the starting looks |
| Grade targets | `plugins/buwan/kit/grade/targets.json` — recalibrate: `node plugins/buwan/scripts/grade-check.js calibrate <reference stills> --look warm --targets plugins/buwan/kit/grade/targets.json` |
| Fonts and logo | `plugins/buwan/kit/fonts`, `plugins/buwan/kit/logo` (fonts are SIL OFL — keep the OFL-*.txt files) |
| Kit graphics | Edit the Video Kit artifact, then save its page as `plugins/buwan/reference/video-kit.html` (and any images into `reference/assets/`). The renderer reads that file, so every editor's graphics update after `/buwan:setup-kit` |
| Assemble engine (cull thresholds, cut-rate targets, b-roll-by-beat table, music levels) | `plugins/buwan/assemble/` — `cull.py` (MIN_SEC, thresholds), `timeline.py` (BEAT_BROLL, targets, defaults in `build_plan`), `fcpxml.py` (writer). Run `assemble.js selftest <folder>` after any change; it must print SELFTEST PASS |
| Premiere bridge version | `plugins/buwan-premiere/scripts/launch-premiere-mcp.js` (and reinstall the panel at the same version on every Premiere machine) |

## Releasing a change
1. Edit the files.
2. Bump `version` in the changed plugin's `.claude-plugin/plugin.json` (1.0.0 → 1.0.1 for wording, 1.1.0 for new rules). **Without a version bump, editors stay on the old rules.**
3. Add a line to `CHANGELOG.md`.
4. Commit and push to `main`.
5. Tell editors: `/plugin marketplace update buwan-films`, then restart Claude Code.
6. Update the Edit Pipeline / Video Kit artifact so the picture matches, and copy the new page into `plugins/buwan/reference/`.

## Adding an editor
1. GitHub → this repo → Settings → Collaborators → add their GitHub account (Read access).
2. They follow the README "Editor setup".

## Removing an editor
Remove them as a collaborator. Their installed copy stops updating.
