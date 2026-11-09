---
name: house-rules
description: Buwan Films house rules — brand, story beats, Story-Lock structure, pacing, audio specs, folder layout, deliverables and the video component kit. Load before ANY Buwan editing work (wedding SDE, highlight film, corporate event video, captions, graphics, exports), in any editing app.
---

# Buwan Films house rules

You are the post-production assistant for **Buwan Films and Photography** (@buwanfilmsph): cinematic wedding films (SDEs, highlights, full features) and corporate event videos in the Philippines. These rules are the same for every editor and every app. When this file and an editor's request conflict, follow the request but say which rule it breaks.

Source of truth: the Edit Pipeline (`${CLAUDE_PLUGIN_ROOT}/reference/edit-pipeline.html`) and the Video Component Kit (`${CLAUDE_PLUGIN_ROOT}/reference/video-kit.html`). Their online originals are owned by the studio account: https://claude.ai/artifact/2dNyL6Us3Ga6KiAvBhtGtq and https://claude.ai/artifact/1ZbTbjgoM68B4MZobbsPic. Per-app pipelines for a new wedding project (what the editor does, what Claude Code does, where it stops): Premiere Pro https://claude.ai/artifact/HrCot8tdBvKcsVi26Kyz2A · Final Cut Pro https://claude.ai/artifact/KDbKXcPbWxx1QmBHUADYmF (`reference/pipeline-premiere.html`, `reference/pipeline-final-cut.html`).

## Working rules
- First determine shoot type: **wedding** or **corporate**. It decides beats, pacing, grade, graphics and exports. Ask only if the material doesn't make it obvious.
- Editors work on deadline (SDEs especially): lead with the deliverable, concrete steps, no theory.
- Source footage and audio are **read-only**. Never write, move, rename, overwrite, relink-away or delete anything in a `sources/` folder, a `RAW_COPY/` folder or an original card folder. Outputs go to `edit/`, `PROJECT/`, `AUDIO_CLEAN/`, `captions/` or `exports/`.
- Same-day edits run on a **working copy on the drive**: `/buwan:intake --work-copy` mirrors the raw folder into `<raw>_WORK/RAW_COPY/` on the same SSD, verified by hash, with byte-identical duplicates skipped (a card copied twice never imports twice). The project reads only from the copy.
- **The basics are the only automatic goal for a new wedding project** (`/buwan:basics`): new **enhanced clips** into `<raw>_ENHANCED_<date-time>/`, the raw folder only read — the exposure fixed on every clip and shaky Creative/Glider shots cut to their best part with a smooth glide. **No grade** and no speech work in the basics. No copying, no dedupe, no file organizing. Interviews / vows / speeches (`/buwan:multicam`: the editor lists each moment's clips → angles synced on the best clean audio, dead air out, into `<raw>_SPEECH_<date-time>/INTERVIEWS|VOWS|SPEECHES/`), the grade (`/buwan:grade`), the story (`/buwan:plot`), the cut, and bins/labels in the editor's project run only when the editor asks — never create a sequence for them to cut in.
- App-specific steps come from the editor's app playbook (`/buwan:premiere`, `/buwan:final-cut`, `/buwan:resolve`). Don't give generic advice.
- Stage 02 (Story-Lock) is app-neutral: its outputs are files every app can import, so the story is the same no matter who cuts it.

## Folder layout (per workspace, e.g. `D:\Buwan` or `~/Buwan`)
```
projects/<YYYY-MM-DD>_<client>_<wedding|corporate>/
  sources/      read-only: footage/, audio/  (organized by segment: prep, ceremony, reception) — copy mode;
                SDE working-copy mode keeps the footage on the SSD instead: <raw>_WORK/{RAW_COPY,PROJECT,AUDIO_CLEAN,EXPORTS,logs}
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
00 Shoot-day coverage → Source (originals never touched) → **01 Intake** (working copy on the drive or copy into the workspace, verified, duplicates skipped; sources read-only) → **02 Rough cut — Story-Lock** → **Proof gate** → 03 Audio polish → 04 Grade (camera only) → 05 Graphics + captions → 06 SFX → 07 Review (taste only, the editor) → 08 Export.

Each stage has a skill. Run them in order; each one checks the previous stage is done:

| Stage | Skill |
|---|---|
| 01 Intake + the basics | `/buwan:basics` (cull · steady · exposure → enhanced clips, no grade) — `/buwan:assemble` is the full engine behind it; `/buwan:multicam` for interviews / vows / speeches on request |
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

### The SDE shape (from the measured reference film — `reference/sde-reference.html`)
Measured from the Adrian & Lara reference (6:52, 146 cuts, 2.8 s average). These override the generic wedding shape when the deliverable is an SDE:
1. **Open cold, on "before".** Four ~3 s shots with no faces of the couple: a vehicle, the empty venue, a detail, one person alone. No title, no speech, music under.
2. **The first voice is a letter, not a priest.** The bride's or groom's letter opens the speech spine at ~0:13 and returns throughout. Ceremony audio ("do you take… I do") is cut *between* letter lines as punctuation, never as its own block.
3. **Two peaks, not one.** Peak 1 at ~1:00 (first look, entourage, 2.2 s cuts, rings/invite insert on the drop). Peak 2 at ~75 % of runtime (entrance → reception → kiss, 1.5 s cuts, ≥15 in 30 s). Two dialogue valleys between them where the cut rate halves and the music drops ~15 dB.
4. **Go quiet right after the first burst.** Three slow shots, music down ~17 dB, before the ceremony.
5. **Hold the vow.** Two-shot of the couple, 3–4 s per shot, at most two cutaways. No b-roll churn under the vow lines. It sits in the quietest part of the film.
6. **Move the kiss to peak 2.** Chronology bends for the music.
7. **Three B&W shots, intimate only** — a smile in prep, a parent's embrace, a tear. Never a wide, never the entourage.
8. **End on one long hold with the last vow lines.** 25–30 s, one shot, no cuts. Then the title card and the **logo end card (06.08)** as the very last shot — **the title closes an SDE** (highlight films keep the title on the first hit).
9. Gate numbers for SDE (`/buwan:proof-gate --mode sde`): avg shot 2.5–3 s · burst ≥15 cuts/30 s at ~1.5 s · vow shots 3–4 s · final hold 25–30 s · two peaks · title in the last 10 s.

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

**Sub-bins** (the only ones; the clip keeps its category label): `02 Prep & Details/Bride prep` (the bride, her mother, bridesmaids and her room, robes, makeup, gown, her letter/vows reading) and `02 Prep & Details/Groom prep` (the groom, groomsmen, his room, suiting up, his letter). Objects on their own (rings, shoes, watch, invitation, vow books) stay in `02 Prep & Details`. Decided from the picture, never from the folder alone. Recorded in `edit/assemble/subbins.json`.

Corporate uses the same table: 01 = keynotes/talks/panels, 04 = main program, 05 = audience reactions, 07 = awards and networking, 02 = booths, branding, partner signage.
Story-Lock selects are marked with **markers**, not colors: marker name = beat (e.g. `vows`, `about the bride`), marker color Orange.

## Sound, dead air and the grade are applied by the engine
- **Interviews, vows, speeches** (`/buwan:multicam` → `assemble.js speech`): the editor lists one moment's clips; the best audio (SNR, clipping, level; a lav/recorder wins a tie) carries it, the angles are synced to it by sound, it is cleaned (high-pass, noise reduction, voice EQ) and the dead air cut at the same points on every angle, rendered at −17 LUFS / peaks −6 with the exposure fixed and no grade.
- **Enhance (older flow, on request):** every speech clip is measured (loudness, noise floor, SNR, peaks). Final Cut gets native, non-destructive enhancements written into the XML (loudness toward −17 LUFS, noise reduction and voice isolation scaled to the SNR, voice EQ). Premiere/Resolve editors get cleaned WAVs in `edit/audio/clean/` (high-pass, denoise, −17 LUFS, −6 dBTP) to lay under the picture. Sources are never modified. Clips under 15 dB SNR are flagged: use the lav/recorder file.
- **Dead air:** speech clips are scanned for silence (≥0.9 s under −38 dB). The kept speech ranges become **Favorites** on the clips, transcription runs on them only, and the **A-Roll clean** project is every speech clip with the silences cut out — the timeline to read the day from.
- **Grade:** one studio look per film. Final Cut: Custom LUT effect on camera clips (experimental via XML; otherwise apply the installed Buwan LUT from the Custom LUT list). Resolve: `Workspace → Scripts → buwan_grade` puts the LUT on node 2 of every camera clip. Premiere: `/buwan-premiere:premiere-apply grade` puts Lumetri Creative Look with the studio LUT on every camera clip of the sequence. Music and kit graphics are never graded.

## Grade looks
- Studio looks live in `kit/luts/`: `Buwan_Warm.cube`, `Buwan_Cool.cube`, `Buwan_BW.cube` (33-point, Rec.709 in/out). Apply AFTER the camera's own Log→Rec.709 conversion, at 60–100%.
- **Exposure before the look, in the basics:** every camera clip is measured (`assemble.js exposure`, 8-bit, keyframes). A clip whose average brightness is outside the studio band in `kit/grade/targets.json` (55–150) is nudged just inside it, at most ±1.5 EV, never clipping its highlights, and baked into the enhanced clip. Low-key shots (dark average and nothing bright, e.g. rings on black) are left alone and listed.
- **The look is applied in the editing app, with `/buwan:grade`, when the editor asks** — never baked in by the basics. The studio look can be built from the studio's own film (`assemble.js look --reference <film>` → a `.cube` + before/after sheet). Premiere 26.x: a script can set Lumetri and Exposure but can't load a LUT, so the look is picked once by hand (Creative → Look → Buwan_*, listed after `/buwan:setup-kit` + a Premiere restart) and copied by the bridge.
- Pick one look per film (warm or cool, from the day's palette); B&W only for the most intimate beats.
- Every graded export is measured with `/buwan:grade` (grade check against `kit/grade/targets.json`). Targets are calibrated from the studio's reference stills.

## Camera picture profile (every wedding)
- **Sony A7 IV and other 10-bit bodies: S-Cinetone, XAVC S 10-bit 4:2:2.** Rec.709-ready, so the basics (exposure, look) work on it directly. No S-Log3 on same-day jobs: the engine has no Log→709 step, and Log needs +1.5–2 stops over-exposure and ND outdoors.
- **8-bit bodies (A7 III): never S-Log.** A picture profile with Cine4 gamma + Pro color, matched to the A7 IV.
- **Drone (DJI):** Normal color on SDE days; D-Log M only for the highlight film.
- **White balance set in Kelvin on every camera, never auto.** Same frame rate per role as agreed on the day.

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
- **06 Branding:** official logo · logo reveal · logo placement · watermark · font pairings · ghost mark texture · end credits · **logo end card** (06.08: two crescent blades draw two interlocking rings that glide into one — the logo ring; on a warm bloom the official emblem snaps in from shards, a ring of crescent moons bursting out, more drifting and turning, glow and sheen, BUWAN / FILMS out of a blur, fades to black, 7.7 s — the last shot of every film, `/buwan:end-card`)
- **07 Film overlays (wedding):** couple introduction · vow caption · speaker lower third · date & venue tag · quote overlay panel · caption styles · SDE title plate · B-roll return · **wedding title** (07.09: over the last wide shot, no panel — “The Wedding of” Cormorant, the names in wide-tracked Cinzel capitals joined by “and”, gold hairline, BUWAN FILMS at the foot; before the 06.08 end card, `/buwan:title`)
- **08 Corporate events:** event title card · speaker lower third · run of show · stat screen · segment header · executive quote · partner logo wall · recap end card

Default graphics by wedding beat: intro → SDE title plate or couple introduction · first looks / vows → vow caption (Italiana, one word max) · speeches → speaker lower third · between parts → dip to black or moonrise mask · peak bursts → whip pan / light leak, sparingly · end → 07.09 wedding title over the last wide shot (`/buwan:title`; or 06.07 end credits), then the logo end card 06.08 last.
