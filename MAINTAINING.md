# Maintaining the Buwan rules (studio owner)

The rules live in this repository. The claude.ai artifacts are the visual versions for people.

## Where each rule lives
| Change | Edit |
|---|---|
| Brand, beats, pacing targets, audio specs, deliverables, kit index | `plugins/buwan/skills/house-rules/SKILL.md` |
| Pacing numbers the gate measures | `plugins/buwan/scripts/proof-gate.js` (keep in sync with house-rules) |
| Stage steps | `plugins/buwan/skills/{intake,plot,proof-gate,export}/SKILL.md` |
| App steps | `plugins/buwan/skills/{premiere,final-cut,resolve}/SKILL.md` |
| What's protected | `plugins/buwan/scripts/protect-sources.js` |
| Rule card every session starts with | `plugins/buwan/scripts/session-start.js` |
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
