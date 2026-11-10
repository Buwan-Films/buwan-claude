---
name: sync
description: New clips during an ongoing wedding — the shooters keep dropping cards into the raw folders; Claude Code finds only the clips that are new since the last run, checks them (cull), fixes their exposure, cuts and smooths shaky Creative/Glider ones, and renders them into the same <raw>_ENHANCED_<date-time>/ folder as before. Clips already there are skipped; the raw folder is only read. Use when an editor says "sync", "new clips", "new cards", "new footage came in", "process the new raws", "update the enhanced folder", or during the day after /buwan:basics. Not camera/audio sync — that is /buwan:multicam.
argument-hint: "<YYYY-MM-DD>_<Couple> [--footage <raw folder>] [--out <_ENHANCED_ folder>]"
---

# Sync — the new clips only

Load `/buwan:house-rules`. Same rules as `/buwan:basics`: the raw folder is only read, no grade, no copying, no sorting. Arguments: $ARGUMENTS

Run after `/buwan:basics` has made the first `_ENHANCED_` folder for the wedding. (On a project with no basics run yet, this is the basics: it makes the first folder.)

## Run
```
node "${CLAUDE_PLUGIN_ROOT}/scripts/assemble.js" update <project> [--footage "<raw folder>"]
```
- Finds the clips that are new since the last run (the raw folder from `edit/SOURCES.md`, or `--footage`).
- Checks only those (cull), judges only the new shaky Creative/Glider clips, measures only their exposure — everything checked before is reused.
- Renders into the **newest** `<raw>_ENHANCED_*` folder next to the raw (or `--out <folder>`); clips already there are skipped. `--new-folder` starts a new folder instead.
- `edit/assemble/update_last.json` lists the new clips of this run.

## Report
A short table: new clips found (per camera) · rendered · left out by the cull (with why) · shaky clips cut/smoothed · the folder. Then the one line to act on:
- **Premiere:** File → Import the new files (they're listed), or drag them from the Media Browser into their camera bin.
- **Final Cut:** File → Import → Media → the same `_ENHANCED_` folder, **Leave files in place**; Final Cut skips what's already in the library.

If the new clips hold a speech, vows or an interview, the editor runs `/buwan:multicam` for that moment with the clip names.

## All day
Run it each time a shooter drops a card. To have it check on its own, the editor can start `/loop 20m /buwan:sync <project>` and stop it with Esc when the day is done.
