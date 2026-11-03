---
name: rough-cut
description: Pipeline stage 02 step 2d — build the picture cut on top of the locked Story-Lock speech spine - b-roll last, serving the story, with bursts and holds placed to the house pacing - then hand to the proof gate. Use when an editor says rough cut, add b-roll, build the cut, picture cut, or after /buwan:plot is approved.
argument-hint: "[project folder] [paper edit version]"
---

# 02 Rough cut — b-roll and picture cut

Prerequisites: an approved `edit/paper-edit_vN.md` and `edit/selects_vN.edl` from `/buwan:plot`, and `edit/clip-log.csv` from `/buwan:organize`. If either is missing, run that first.

## Rules (from the Edit Pipeline)
- The speech spine is locked. Don't reorder or trim lines without the editor's OK.
- **B-roll last, serving the story**: every shot matches or elevates the line under it — never decoration.
- Pacing: bursts ~1–2s/shot at the energy peak (up to ~30 cuts/30s), **15–20s unbroken holds** on vows and first looks, average ~2.5–3s. Corporate: steady 1.5–2.5s, holds on speakers.
- Cuts land on beat and on key words.

## Steps
1. **Shot plan** — for each line in the paper edit, choose b-roll from the clip log by category:
   - speech about a person → that person's Portraits/Prep shots
   - emotional peak → Reactions & BTS (burst bank)
   - between parts and after big lines → Establishing (breathing room)
   - vows / first looks → hold on the speaker or the moment itself, no cutaways
   Write `edit/shot-plan_vN.md`: `line # · record TC · b-roll clip · src in · src out · why`.
2. **Beat grid** — once the editor has chosen the music (`/buwan:plot` gives the music feel), get the beats: the editor's beat markers exported from the app, or, if Python with `librosa` is installed, `librosa.beat.beat_track` on the music file. Save `edit/beats.csv` (seconds). Snap burst cuts to beats; snap speech-led cuts to word ends from the transcript.
3. **Build** the cut in the editor's app as a NEW sequence/timeline `Rough Cut vN`:
   - Premiere: through the bridge (V1 speech-led picture, V2 b-roll, A1–A2 speech, A3–A4 music).
   - Resolve: write `edit/rough-cut_vN.edl` (V1) + import, or FCPXML for multi-track.
   - Final Cut: write `edit/rough-cut_vN.fcpxml` (spine = speech-led picture, connected b-roll).
4. **Measure**: export the picture track as CMX3600 → `/buwan:proof-gate` (mode cut). Fix FAILs before handing over.
5. **Handover**: what's in the cut, gate results, open questions (missing coverage, weak b-roll spots).

Same-day mode: skip the shot-plan file — build straight from the paper edit, one pass.
