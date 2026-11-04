# Maintaining the Buwan rules (studio owner)

The rules live in this repository. The claude.ai artifacts are the visual versions for people.

## Where each rule lives
| Change | Edit |
|---|---|
| Brand, beats, pacing targets, audio specs, deliverables, kit index | `plugins/buwan/skills/house-rules/SKILL.md` |
| Pacing numbers the gate measures | `plugins/buwan/scripts/proof-gate.js` (keep in sync with house-rules) |
| Stage steps | `plugins/buwan/skills/<stage>/SKILL.md` (intake, organize, plot, rough-cut, proof-gate, audio, grade, graphics, sfx, review, export, clipper, sde) |
| App steps | `plugins/buwan/skills/{premiere,final-cut,resolve}/SKILL.md` |
| What's protected | `plugins/buwan/scripts/protect-sources.js` |
| Rule card every session starts with | `plugins/buwan/scripts/session-start.js` |
| Clip categories, bins, colors | `house-rules/SKILL.md` → "Clip categories, bins and colors" (and `skills/organize`) |
| Studio looks | `plugins/buwan/kit/luts/*.cube` — replace with LUTs exported from your reference grade (Resolve: right-click node → Generate LUT → 33 Point Cube). `tools/make-luts.py` regenerates the starting looks |
| Grade targets | `plugins/buwan/kit/grade/targets.json` — recalibrate: `node plugins/buwan/scripts/grade-check.js calibrate <reference stills> --look warm --targets plugins/buwan/kit/grade/targets.json` |
| Fonts and logo | `plugins/buwan/kit/fonts`, `plugins/buwan/kit/logo` (fonts are SIL OFL — keep the OFL-*.txt files) |
| Kit graphics | Edit the Video Kit artifact, then save its page as `plugins/buwan/reference/video-kit.html` (and any images into `reference/assets/`). The renderer reads that file, so every editor's graphics update after `/buwan:setup-kit` |
| Premiere bridge version | `plugins/buwan-premiere/scripts/launch-premiere-mcp.js` (and reinstall the panel at the same version on every Premiere machine) |

## Releasing a change
1. Edit the files.
2. Bump `version` in the changed plugin's `.claude-plugin/plugin.json` (1.0.0 → 1.0.1 for wording, 1.1.0 for new rules). **Without a version bump, editors stay on the old rules.**
3. Add a line to `CHANGELOG.md`.
4. Commit and push to `main`.
5. Tell editors: `/plugin marketplace update buwan-films`, then restart Claude Code.
6. Update the Edit Pipeline / Video Kit artifact so the picture matches, and copy the new page into `plugins/buwan/reference/`.

## Adding an editor
1. GitHub → [Buwan-Films/buwan-claude](https://github.com/Buwan-Films/buwan-claude) → Settings → Collaborators and teams → add their GitHub account (Read access).
2. They follow the README "Editor setup".

## Removing an editor
Remove them as a collaborator. Their installed copy stops updating.
