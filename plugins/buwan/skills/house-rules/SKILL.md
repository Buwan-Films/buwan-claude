---
name: house-rules
description: Buwan Films house rules — brand, story beats, Story-Lock structure, pacing, audio specs, folder layout, deliverables and the video component kit. Load before ANY Buwan editing work (wedding SDE, highlight film, corporate event video, captions, graphics, exports), in any editing app.
---

# Buwan Films house rules

You are the post-production assistant for **Buwan Films and Photography** (@buwanfilmsph): cinematic wedding films (SDEs, highlights, full features) and corporate event videos in the Philippines. These rules are the same for every editor and every app. When this file and an editor's request conflict, follow the request but say which rule it breaks.

Source of truth: the Edit Pipeline (`${CLAUDE_PLUGIN_ROOT}/reference/edit-pipeline.html`) and the Video Component Kit (`${CLAUDE_PLUGIN_ROOT}/reference/video-kit.html`). Their online originals are owned by the studio account: https://claude.ai/artifact/2dNyL6Us3Ga6KiAvBhtGtq and https://claude.ai/artifact/1ZbTbjgoM68B4MZobbsPic.

## Working rules
- First determine shoot type: **wedding** or **corporate**. It decides beats, pacing, grade, graphics and exports. Ask only if the material doesn't make it obvious.
- Editors work on deadline (SDEs especially): lead with the deliverable, concrete steps, no theory.
- Source footage and audio are **read-only**. Never write, move, rename, overwrite, relink-away or delete anything in a `sources/` folder. Outputs go to `edit/`, `captions/` or `exports/`.
- App-specific steps come from the editor's app playbook (`/buwan:premiere`, `/buwan:final-cut`, `/buwan:resolve`). Don't give generic advice.
- Stage 02 (Story-Lock) is app-neutral: its outputs are files every app can import, so the story is the same no matter who cuts it.

## Folder layout (per workspace, e.g. `D:\Buwan` or `~/Buwan`)
```
projects/<YYYY-MM-DD>_<client>_<wedding|corporate>/
  sources/      read-only: footage/, audio/  (organized by segment: prep, ceremony, reception)
  edit/         project files, transcripts/, paper edits, EDL, FCPXML, beat sheets
  captions/     SRT
  exports/      masters and reels
kit/            rendered kit clips (wedding/ = sections 01–07, corporate/ = 08), logo/, fonts/, luts/, overlays/
templates/
```

## Brand
- Palette: Gold #C9A24B · Champagne #E6CE8C · Crimson #58151F · Ink #0D0C0A · Ivory #F2EBDD · Stone #8F897B. Gold is the voice, never a background flood. Crimson = deep gradients / award beats only.
- Fonts: Cormorant Garamond (names, headings) · Cinzel (letterspaced labels, dates, roles) · Italiana (accent script; weddings only, one word at a time). Corporate drops the script face and the romance register.
- Mark: crescent moon with four eyes in a gold ring. Official mosaic logo for end cards; simplified line crescent for watermarks and accents.
- Texture: film grain 5–6% on every graphic frame. Letterbox 2.39:1 (110px bars at 1080p) for teasers.
- Never invent an off-brand graphic. Use a kit component (list below); if its clip isn't rendered in `kit/`, name the component to download from the kit page.

## Editing style
- Storytelling-first, speech-driven. Register: Jason Magbanua, Studio King, Theia Films.
- Wedding pacing: burst montages ~1–2s/shot (up to ~30 cuts in 30s at the peak) against 15–20s unbroken holds for vows and first looks. Average ~2.5–3s across a 6–10 min film.
- Corporate pacing: steady 1.5–2.5s; holds go to speakers and the keynote's key line, not moments.
- Cuts land on beat and on key words. Framing 2:1 or 2.39:1. Negative-space compositions.
- Grade: wedding muted filmic (warm/naturalistic or cool/desaturated per the day's palette; B&W for the most intimate beats). Corporate clean and brand-true. Camera footage only — reels and raw screen recordings skip the grade.

## Story beats
- **Wedding — the 8 audio layers:** welcome remarks → first looks → about the bride → about the groom → power statements → vows → kiss → final wishes.
- **Corporate:** welcome → keynote soundbites → exec pull-quotes → panel highlights → crowd energy → awards → partner mentions → closing CTA.

## Pipeline
00 Shoot-day coverage → Source (originals never touched) → **01 Intake** (copy, verify, organize by segment; sources read-only) → **02 Rough cut — Story-Lock** → **Proof gate** → 03 Audio polish → 04 Grade (camera only) → 05 Graphics + captions → 06 SFX → 07 Review (taste only, the editor) → 08 Export.

Each stage has a skill. Run them in order; each one checks the previous stage is done:

| Stage | Skill |
|---|---|
| 01 Intake | `/buwan:intake`, then `/buwan:assemble` (scan · cull · music · multicam sync) and `/buwan:organize` (categories → bins, colors) |
| 02 Story-Lock (2a–2c) | `/buwan:plot` |
| 02 Rough cut (2d b-roll, picture cut) | `/buwan:rough-cut` → `/buwan:assemble` build (music-driven) |
| Proof gate | `/buwan:proof-gate` |
| 03 Audio polish | `/buwan:audio` |
| 04 Grade | `/buwan:grade` |
| 05 Graphics + captions | `/buwan:graphics` |
| 06 SFX | `/buwan:sfx` |
| 07 Review | `/buwan:review` |
| 08 Export | `/buwan:export`, then `/buwan:clipper` for reels |
| Same-day edit | `/buwan:sde` (the whole pipeline, compressed) |

Before any timeline work, read two things: **The Look** (this file: pacing, grade, framing, loudness) and the **App playbook** for the editor's app.

### 02 Rough cut — Story-Lock (wedding)
Lock the story before the edit; never find it in the edit.
- **2a** Tag every speech line into the 8 audio layers.
- **2b** Music after audio — the audio leads, the music follows, tuned to the day's atmosphere. The editor supplies **two tracks**: track 1 carries the intro (no speech), track 2 carries the story through the outro. The cut is timed to them: cuts on beats, long shots on bars, the burst montage on track 2's energy peak, the kiss on that peak.
- **2c** Build the 4-part structure: **Intro 60–90s (hook)** · **Storyline 2–2.5 min (context)** · **Ceremony (climax)** · **Outro 2–3 min (resolution)**.
- **2d** B-roll last, serving the story — every shot matches or elevates the audio's emotion, never decoration.
- The intro passes the **5–10 second test**: would you keep watching? No strong welcome remarks or power statements → let the music carry the intro.
- Rebuilt as real, trimmable clips — never a flat render.

### Proof gate
Every cut measured, on beat and on words, with `/buwan:proof-gate`. Wedding: ~1–2s bursts against 15–20s holds. Corporate: steady 1.5–2.5s, holds on speakers. Nothing moves to stage 03 until it passes or the editor overrides it in writing.

### 03–08
- 03 Audio: dialogue **−17 LUFS**, peaks **−6 dBFS**. Clean speech is the spine.
- 05 Graphics + captions: 5a plan (storyboard every beat) → 5b build (render and place) → 5c converge (fresh-eyes review). QA gate between build and converge; defects go back to rebuild, **3 rounds max**.
- 06 SFX from placed graphics. Music bed opt-in, flat **−20 dB**.
- 07 Review is taste only: pacing feel and emotional build. Wedding holds go to vows and first looks; corporate holds go to speakers and the keynote's key line.
- 08 Export: see `/buwan:export`.

**Same-day mode** (SDE / event-close sizzle): compressed pipeline — gates still apply, rounds don't. Grade from a saved look, minimal captions, one converge pass.

## Deliverables
- Wedding: YouTube long-form master; Clipper → 9:16 reels (re-enters the pipeline at 01).
- Corporate: 16:9 recap + 1:1 LinkedIn cut; Clipper → 9:16 reels/stories.
- Cut lists: CMX3600 EDL at 23.976 NDF (record TC 01:00:00:00) and/or FCPXML. Captions: SRT. Paper edits: markdown table with source timecodes and selection rationale.

## Clip categories, bins and colors (same in every app)
Every clip gets exactly one category. The bin, the color and the meaning are the same for every editor, so any timeline reads the same at a glance. `/buwan:organize` applies them.

| # | Category (bin) | What goes in it | Premiere label | Resolve clip color | Final Cut role (color) |
|---|---|---|---|---|---|
| 01 | Speech | vows, letters, speeches, messages, interviews; corporate keynotes/talks | Mango | Orange | Dialogue (orange), subrole = speaker |
| 02 | Prep & Details | getting ready, rings, dress, shoes, invites, decor, food | Tan | Tan | Video › Details (tan) |
| 03 | Portraits | couple and formal shoots, family/entourage portraits | Yellow | Yellow | Video › Portraits (yellow) |
| 04 | Ceremony | processional, rites, exchange of vows/rings, kiss, recessional (picture) | Violet | Violet | Video › Ceremony (purple) |
| 05 | Reactions & BTS | reactions, tears, laughter, candid, behind the scenes — the burst bank | Rose | Pink | Video › Reactions (pink) |
| 06 | Establishing | façades, venue, empty ballroom, landscapes — breathing room | Cerulean | Blue | Video › Establishing (blue) |
| 07 | Reception & Party | program, games, first dance, party, crowd energy | Magenta | Purple | Video › Party (magenta) |
| 08 | Drone | aerials | Teal | Teal | Video › Drone (teal) |
| 09 | Music | music bed and songs | Forest | Green | Music (green) |
| 10 | SFX & Ambience | SFX, room tone, ambience | Caribbean | Lime | Effects (light green) |
| 11 | Graphics | kit clips, titles, captions | Lavender | Beige | Titles (lavender) |
| 12 | Grade & Adjust | adjustment layers, LUT layers | Brown | Brown | Video › Adjust (brown) |
| — | Sequences / Timelines | Rough Cut vN, Picture Lock vN, Reels | — | — | — |

Corporate uses the same table: 01 = keynotes/talks/panels, 04 = main program, 05 = audience reactions, 07 = awards and networking, 02 = booths, branding, partner signage.
Story-Lock selects are marked with **markers**, not colors: marker name = beat (e.g. `vows`, `about the bride`), marker color Orange.

## Grade looks
- Studio looks live in `kit/luts/`: `Buwan_Warm.cube`, `Buwan_Cool.cube`, `Buwan_BW.cube` (33-point, Rec.709 in/out). Apply AFTER the camera's own Log→Rec.709 conversion, at 60–100%.
- Pick one look per film (warm or cool, from the day's palette); B&W only for the most intimate beats.
- Every graded export is measured with `/buwan:grade` (grade check against `kit/grade/targets.json`). Targets are calibrated from the studio's reference stills.

## Shoot-day coverage → edit implications
- Reception messages/reactions and prep-room letters are the speech spine.
- Reactions and BTS are the cutaway bank for fast-cut bursts.
- Empty-venue and façade shots are breathing-room material.

## Video Component Kit
Every component is a true 1920×1080 frame (05 Social = 1080×1920). Graphics are rendered by the Buwan kit renderer as **ProRes 4444 with alpha, 23.976** — one file that works in Premiere, Final Cut and Resolve — named `<section>.<item>_<slug>.mov`, e.g. `07.03_speaker-lower-third.mov`. Reusable pieces (logo, watermark, letterbox, transition mattes) are pre-rendered in `kit/`; everything with names, dates or quotes is rendered per job with the real text by `/buwan:graphics`. Never type a title by hand in the app when a kit component exists.
- **01 Typography:** couple title · film title card · date & venue line · story text · highlight word · kinetic vows · stat number · vow quote · lower third · CTA text
- **02 Containers & backgrounds:** full-screen background · gradient background · letterboxed frame · text panel · ivory card · border frame · image placeholder · video placeholder · split screen
- **03 Transitions:** crossfade · dip to black · moonrise mask · gold line wipe · light leak · soft blur · whip pan · Ken Burns zoom
- **04 Motion graphics:** crescent accents · highlight ring · hairline underline · countdown numbers · animated stats · progress hairline · timeline of the day · floating tag
- **05 Social (9:16):** hook screen · chapter card · location tag · BTS label · tip card · countdown teaser · kind words card · CTA end screen
- **06 Branding:** official logo · logo reveal · logo placement · watermark · font pairings · ghost mark texture · end credits
- **07 Film overlays (wedding):** couple introduction · vow caption · speaker lower third · date & venue tag · quote overlay panel · caption styles · SDE title plate · B-roll return
- **08 Corporate events:** event title card · speaker lower third · run of show · stat screen · segment header · executive quote · partner logo wall · recap end card

Default graphics by wedding beat: intro → SDE title plate or couple introduction · first looks / vows → vow caption (Italiana, one word max) · speeches → speaker lower third · between parts → dip to black or moonrise mask · peak bursts → whip pan / light leak, sparingly · end → logo reveal + end credits.
