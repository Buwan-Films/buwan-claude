---
name: plot
description: Pipeline stage 02 — Story-Lock. "Plot this": transcribe speech, tag lines into the beat system, select and order for emotional build, and deliver the paper edit, EDL/FCPXML and SRT. Use when an editor says "plot", "paper edit", "story lock", "rough cut", or hands over vows, letters, speeches or a transcript.
argument-hint: "[project folder] [highlights|SDE|full|corporate recap] [target length]"
---

# 02 Rough cut — Story-Lock ("plot this")

Follow the house rules (`/buwan:house-rules`). Arguments: $ARGUMENTS

## 1. Transcribe once
- Use existing transcripts first: the app's transcript export (Premiere Text panel, Resolve transcription, FCP captions) or `edit/transcripts/*`.
- Otherwise transcribe the speech clips (local Whisper if installed) and save to `edit/transcripts/<clip>.srt` with source timecodes. Never write transcripts into `sources/`.
- Expect **Taglish**. Keep the original wording. Never clean up, translate or "fix" vows or speeches. Mark unclear words `[?]`.

## 2. Tag
Tag every usable line with one beat: wedding = the 8 audio layers; corporate = the 8 corporate beats. Note the speaker.

## 3. Select and order
- Pick the strongest lines. **Callbacks** (a line echoed later by someone else) and **paired constructions** (bride/groom answering each other, "before/now") rank highest.
- Wedding: build the 4-part structure — Intro 60–90s hook · Storyline 2–2.5 min · Ceremony climax · Outro 2–3 min. Run the 5–10 second test on the intro; if nothing passes it, say "music carries the intro" and leave the intro speech-free.
- Music after audio: recommend the music feel per part from the selected lines; don't choose music first.
- Mark where the 15–20s holds go (vows, first looks) and where the burst montages go (energy peak).
- B-roll is NOT placed at this stage. Only list the b-roll needs per beat (from the coverage: reactions/BTS for bursts, façades/empty venue for breathing room).

## 4. Deliver (in `edit/`)
1. `paper-edit_v<N>.md` — table: `# · part · beat · speaker · source clip · src in · src out · line (verbatim) · why picked`. Then **Left out** (line + reason) and **Music feel per part** and **B-roll needs per beat**. Header: project, editor (`${user_config.editor_name}`), date, version.
2. `selects_v<N>.edl` — CMX3600, 23.976 NDF (timebase 24, non-drop), record TC starting `01:00:00:00`, events in story order, `* FROM CLIP NAME:` comment on every event, reel names ≤ 8 chars or `AX`. Speech selects only.
3. `edit/assemble/selects.json` — the machine-readable Story-Lock: an ordered list of `{"clip": "<absolute path>", "in": <s>, "out": <s>, "beat": "<one of the 8 layers>", "part": "Intro|Storyline|Ceremony|Outro", "speaker": "<name>", "text": "<verbatim line>", "hold": true|false}`. Then build the review project with the engine (never hand-write FCPXML):
   `node "${CLAUDE_PLUGIN_ROOT}/scripts/assemble.js" selects <project> --selects edit/assemble/selects.json --multicam --event "<event>"` → `edit/selects_vN.fcpxml` (Final Cut and Resolve import it).
4. `captions/selects_v<N>.srt` — the selected lines in record time, verbatim.
5. **Proper nouns** — list every name, place, church, venue and brand found, for spot-checking before captions ship.

Then run `/buwan:proof-gate` on the EDL in **speech mode**, and give app import steps from the editor's playbook. If the app has a live bridge (Premiere), offer to build the sequence directly in a NEW sequence named `Rough Cut v<N>`.

Same-day mode: one pass, no alternates, keep the paper edit to the selected lines plus a one-line "left out" summary.
