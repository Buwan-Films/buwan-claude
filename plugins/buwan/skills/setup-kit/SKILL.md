---
name: setup-kit
description: One-time (and after updates) Buwan kit setup on an editor's computer - installs the brand fonts, copies logo/LUTs/grade targets into the workspace kit folder, installs the kit renderer, and renders the reusable kit clips. Use when an editor says setup kit, install fonts, kit missing, update kit, or /buwan:check reports kit or fonts missing.
---

# Set up the Buwan kit on this computer

Run from the editor's Buwan workspace folder (it has `projects/`). Takes 3–6 minutes the first time.

1. Check prerequisites: `node --version` (≥ 20.19), `ffmpeg -version`. If ffmpeg is missing: Windows `winget install Gyan.FFmpeg`, macOS `brew install ffmpeg`, then restart the terminal and Claude Code.
2. Run:
   ```
   node "${CLAUDE_PLUGIN_ROOT}/scripts/setup-kit.js" --workspace "<workspace folder>"
   ```
   It installs the fonts for this user, copies `kit/logo`, `kit/fonts`, `kit/luts`, `kit/grade` into the workspace, installs Playwright + Chromium for the renderer (in `~/.buwan/deps`, where the renderer looks for it), and renders the reusable clips into `kit/wedding/` and `kit/transitions/`.
3. Show the editor the PASS/FAIL table. Tell them to **restart their editing app** so the fonts appear.

Re-run after every plugin update that mentions kit changes (CHANGELOG). Re-running is safe: it overwrites kit files with the studio's current versions, and never touches `projects/`.
