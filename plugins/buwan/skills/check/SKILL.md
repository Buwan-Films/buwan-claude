---
name: check
description: Verify this editor's Buwan setup — plugin version, editing app, workspace folders, kit, source protection and app bridge. Use when an editor says "check setup", "verify", or before their first client job.
---

# Buwan setup check

Make no changes. Report a PASS / FAIL table with a fix for each FAIL:

1. Buwan plugin loaded — state the plugin version from `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json`, the editor name (`${user_config.editor_name}`) and editing app (`${user_config.nle}`).
2. House rules understood — state the 8 wedding audio layers in order, the 4-part structure with durations, and the audio specs.
3. Workspace — current folder has `projects/`, `kit/` (wedding, corporate, logo, fonts, luts, overlays) and `templates/`. If missing, offer to create them.
4. Kit — workspace `kit/` has `logo/`, `fonts/`, `luts/` (Buwan_Warm/Cool/BW.cube), `grade/targets.json`, and the pre-rendered clips in `kit/wedding/` and `kit/transitions/`. If not, run `/buwan:setup-kit`.
5. Fonts — Cormorant Garamond, Cinzel and Italiana installed for this user (Windows: `%LOCALAPPDATA%\Microsoft\Windows\Fonts`; macOS: `~/Library/Fonts`). If not, `/buwan:setup-kit`.
5b. Renderer — `node "${CLAUDE_PLUGIN_ROOT}/scripts/render-kit.js" list` prints the component list (Playwright installed).
6. Tools — `node --version` ≥ 20.19, `ffmpeg -version`, `ffprobe -version`.
7. Source protection — confirm the read-only hook is active by explaining what you would refuse to do in a `sources/` folder (do not test it by writing there).
8. App bridge — Premiere: run "Verify Premiere connection" (needs the buwan-premiere plugin and the MCP Bridge panel open). Final Cut: none, FCPXML import. Resolve: none by default, EDL/FCPXML import.
