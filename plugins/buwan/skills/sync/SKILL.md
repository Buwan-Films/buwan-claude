---
name: sync
description: New clips during an ongoing wedding — the shooters keep dropping cards into the raw folders; Claude Code finds only the clips that are new since the last run, checks them (cull), fixes their exposure and white balance, cuts and smooths shaky Creative/Glider ones, renders the ones with a fix and copies the rest as they are into the same <raw>_ENHANCED_<date-time>/ folder as before, then transcribes every clip with speech (local whisper) so /buwan:plot starts from text. Clips already there are skipped; the raw folder is only read. Use when an editor says "sync", "new clips", "new cards", "new footage came in", "process the new raws", "update the enhanced folder", or during the day after /buwan:basics. Not camera/audio sync — that is /buwan:multicam.
argument-hint: "<YYYY-MM-DD>_<Couple> [--footage <raw folder>] [--out <_ENHANCED_ folder>]"
---

# Sync — the new clips only

Load `/buwan:house-rules`. Same rules as `/buwan:basics`: the raw folder is only read, no grade, no working copy, no sorting. New clips with a fix are rendered, new clips with no fix are copied as they are, so the folder keeps every clip of the day. Arguments: $ARGUMENTS

Run after `/buwan:basics` has made the first `_ENHANCED_` folder for the wedding. (On a project with no basics run yet, this is the basics: it makes the first folder.)

## Run
```
node "${CLAUDE_PLUGIN_ROOT}/scripts/assemble.js" update <project> [--footage "<raw folder>"]
```
- Finds the clips that are new since the last run (the raw folder from `edit/SOURCES.md`, or `--footage`).
- Checks only those (cull), judges only the new shaky Creative/Glider clips, measures only their exposure and white balance — everything checked before is reused.
- Renders into the **newest** `<raw>_ENHANCED_*` folder next to the raw (or `--out <folder>`); clips already there are skipped. `--new-folder` starts a new folder instead.
- `edit/assemble/update_last.json` lists the new clips of this run.
- **Then transcribes** (after the render, so the clips reach the editor first): every camera clip with sound, ≥ 20 s, not culled, not aerial, that has no transcript yet — on the first sync after the basics that includes the basics' clips. Local whisper.cpp large-v3-turbo with voice detection, nothing leaves the computer, ~35× real time (a 12-min ceremony clip in ~20 s). Out: `edit/transcripts/<camera>/<card>/<clip>.srt` + `.txt` (verbatim, Taglish as spoken), `edit/assemble/transcripts.json`, and `edit/transcripts_report.md` (the clips with speech, what they sound like — vows · mass · speech/toast · interview/message · talk, a guess — and the first words). `--no-transcribe` skips it; `--language tl|en` forces the language (default auto). Needs `whisper-cli` and the model (`/buwan:setup-kit`); without them it says so and the rest of the sync is unaffected.
- On its own: `assemble.js transcribe <project> [--clips C0823 C0906]`.

## Report
A short table: new clips found (per camera) · rendered · left out by the cull (with why) · shaky clips cut/smoothed · transcribed (with speech: clip · sounds like · first words) · the folder. Then the one line to act on:
- **Premiere:** with the MCP Bridge panel open, `assemble.js premiere-import <project>` → bridge step `enhanced` (`/buwan-premiere:premiere-apply`): the new files go into their camera bins, speech clips Mango with their first words in Description. Without the bridge: File → Import the new files (they're listed).
- **Final Cut:** File → Import → Media → the same `_ENHANCED_` folder, **Leave files in place**; Final Cut skips what's already in the library.

If the new clips hold a speech, vows or an interview, the editor runs `/buwan:multicam` for that moment with the clip names.

## All day
Run it each time a shooter drops a card. To have it check on its own, the editor can start `/loop 20m /buwan:sync <project>` and stop it with Esc when the day is done.
