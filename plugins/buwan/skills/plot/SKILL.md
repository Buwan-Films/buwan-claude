---
name: plot
description: Pipeline stage 02 — Story-Lock. "Plot this": transcribe speech, tag lines into the beat system, select and order for emotional build, and deliver the paper edit, EDL/FCPXML and SRT. Use when an editor says "plot", "paper edit", "story lock", "rough cut", or hands over vows, letters, speeches or a transcript.
argument-hint: "[project folder] [highlights|SDE|full|corporate recap] [target length]"
---

# 02 Rough cut — Story-Lock ("plot this")

Follow the house rules (`/buwan:house-rules`). Arguments: $ARGUMENTS

## 0. Start from the storyboard (when there is one)
If `edit/storyboard/storyboard.json` exists (the Storyboard page's export, unzipped into `edit/storyboard/`), it is the plan the client signed off: beat order, the kind of each beat (`aroll` speaker on screen · `broll` line under footage · `card` · `montage` music only), hold/burst, the music switch (`track` 1/2) and the card text. Use it as the skeleton:
- Put the real transcript lines into the planned beats. Planned `words` are placeholders unless they match the transcript — never put a line on screen that nobody said.
- A planned beat with no matching line: say so in the paper edit (**Planned, not found**) and suggest a montage or a cut; don't invent.
- A strong line that fits no planned beat: still offer it, marked **Not in the storyboard**. The day wins over the plan.
- Keep the storyboard's beat ids in the paper edit (`beat` column) so the rough cut, graphics and review can match them.
- **Commercial / reels: Script-Lock.** The client approves the script (voice-over, supers, talent lines) before the shoot; it is the storyboard. At Story-Lock pick the best take of every scripted line and the testimonial lines exactly as said — never rewrite a testimonial or add a claim. Supers and claims come only from the approved script.
- **Prenup:** there is usually no speech. The storyboard's shot flow is the story; Story-Lock becomes **Shot-Lock**: the best take per planned shot (from the shot list's `clips`), in storyboard order, written as the paper edit with `line` = the shot. Voice-over lines, if recorded, follow the speech rules.

## 1. Transcribe once
- Use existing transcripts first: `edit/transcripts_report.md` + `edit/assemble/transcripts.json` (made by `/buwan:sync`: every clip with speech, `edit/transcripts/<camera>/<card>/<clip>.srt`), the app's transcript export (Premiere Text panel, Resolve transcription, FCP captions) or `edit/transcripts/*`. Missing clips: `assemble.js transcribe <project> --clips <names>`.
- If `edit/assemble/speech_ranges.json` exists, transcribe only those ranges (the dead air is already removed).
- Otherwise transcribe the speech clips (local Whisper if installed) and save to `edit/transcripts/<clip>.srt` with source timecodes. Never write transcripts into `sources/`.
- Expect **Taglish**. Keep the original wording. Never clean up, translate or "fix" vows or speeches. Mark unclear words `[?]`.

## 2. Tag
Tag every usable line with one beat: wedding = the 8 audio layers; corporate = the 8 corporate beats; commercial = hook · problem / need · brand or product hero · features · people using it · testimonial · offer · call to action · logo; prenup = the storyboard's shot flow (teaser open · her · him · together · playful · details · intimate · golden hour · closing). Note the speaker (camera + voice; confirm names with the editor — "Speaker 3 = Tito Terry").

**Controls the editor can set (ask once; defaults in brackets):** speakers to include [couple + family + best friends; MC/host excluded]; story focus [personal vows & journey, family, friends' stories, ceremony moments]; content to exclude [legal formalities, MC talking, vendor/supplier mentions, "thank you for coming" speeches]; film length [SDE 4–7 min, highlights 6–10]; dialogue density [medium]. SDE: the letters outrank the ceremony audio — a letter opens the spine; "do you take / I do" is punctuation between letter lines.

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
