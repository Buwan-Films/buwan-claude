---
name: multicam
description: Interviews, vows and speeches on request — the editor lists the clips of one moment (every camera angle plus a lav/recorder file); Claude Code picks the best audio, syncs the angles to it by sound, cleans that audio (−17 LUFS, peaks −6), cuts the dead air at the same points on every angle, and renders each angle with its exposure and white balance fixed (no grade) into <raw>_SPEECH_<date-time>/INTERVIEWS|VOWS|SPEECHES/<moment>/, ready for a multicam in any app. Not part of the basics. Use when an editor says "multicam", "merge the angles", "sync the vows / interview / speech", "best audio", "dead air", or lists clips of one moment.
argument-hint: "<project> --moment \"<name>\" --type <interview|vows|speech> --clips <clip> <clip> …"
---

# Interviews, vows and speeches (on request)

Load `/buwan:house-rules`. The raw folder is only read; every run writes into a new `<raw>_SPEECH_<YYYYMMDD-HHMM>/` next to it. Arguments: $ARGUMENTS

## 1. The editor lists the moments
The editor gives the clip names — use exactly the clips they list, never add or swap one. For each moment: a name, the type, and its clips, every angle plus the lav/recorder file if there is one. Clip names are enough (`C0823`, `C0017.MP4`, `ZOOM0003`): the engine finds each one under the raw folder. If two cameras have a clip with the same name, it stops and lists them; then add the camera folder (`2-Main/C0823`, or just `Main/C0823`). Full paths and paths relative to the raw folder work too. Example:
`/buwan:multicam 2026-04-18_Marynhor-Jomar --moment "Bride vows" --type vows --clips C0823 C0017 ZOOM0003`
If the editor only names the moment and asks Claude to find the clips, look at one frame per likely clip (same time window, same people) and confirm the list with them before rendering. Types: `interview` → `INTERVIEWS/`, `vows` → `VOWS/`, `speech` → `SPEECHES/` (letters read on camera: interview).

## 2. Run
`node "${CLAUDE_PLUGIN_ROOT}/scripts/assemble.js" speech <project> --moment "<name>" --type <type> --clips <clip> <clip> …`
(each moment is remembered in `edit/assemble/speech_moments.json`; `speech <project>` alone re-runs them all into a new folder; `--out <earlier _SPEECH_ folder>` adds to it).

What it does, per moment:
1. **Best audio** — every clip's sound measured (signal-to-noise, clipping, level); the best one carries the moment. A lav/recorder file wins a tie.
2. **Sync** — every other clip placed against the best audio by sound (cross-correlation, refined to 2.5 ms), so wrong camera clocks don't matter. A clip that doesn't match is left out and listed ("check it's the same moment"); a clip with no sound is listed to place by hand.
3. **Clean** — high-pass, noise reduction scaled to the noise, voice EQ, levelled.
4. **Dead air** — silences between words (≥ 0.9 s) cut out, the same cuts on every angle so they stay in sync, 20 ms fades at the joins. Words are never cut: vows and speeches stay verbatim.
5. **Render** — each video angle: the kept ranges, the exposure and white balance fix (from `exposure.json`, or measured now), no grade, HEVC 10-bit, the one clean audio at −17 LUFS / peaks −6 dBFS. Each angle holds only the part it covered and **starts at the timecode of where that sits in the cut moment** (the moment starts at 00:00:00:00), so the angles line up by timecode in any app.

Output per moment: `<camera>_<clip>.mov` per angle, `<moment>_audio.wav` (the clean audio alone, the whole cut moment), `moment.json` (best audio, offsets, start timecodes, kept ranges, what was left out).

## 3. Report and hand-off
Per moment: angles · best audio (which file, SNR) · minutes kept / dead air removed · clips left out and why. Then:
- **Premiere:** import the moment folder, select the angles → right-click → **Create Multi-Camera Source Sequence** → Synchronize Point: **Timecode**; audio: any angle (every angle carries the clean audio), or the longest one.
- **Final Cut:** select the angles → **New Multicam Clip** → Use Custom Settings → Angle Synchronization: **Timecode**.
- **Resolve:** select the angles → **Create New Multicam Clip Using Selected Clips** → Angle Sync: **Timecode**.

## Rules
- Never write into the raw folder. Nothing in the basics' `_ENHANCED_` folder is touched.
- If every clip's audio is silent (the camera mic was off), stop and ask for the lav/recorder file.
- Whole-day multicam groups (every camera, by timestamp + sound) are still `assemble.js sync <project> --anchor … --trusted …`, only when asked.
