---
name: assemble
description: Buwan footage prep + music-driven first cut in one run — scan the raw footage, cull unusable clips, analyse the two music tracks, sync every camera by sound (multicam), organize into the studio bins/colors, then (after Story-Lock) build a timeline cut to the music with the kiss on the music peak. Use when an editor says assemble, prep the footage, sync cameras, multicam, "cut it to the music", "build the SDE", or drops footage + music in a folder.
argument-hint: "<project folder> [--footage <dir>] [--music <dir>]"
---

# Assemble — footage prep and the music-driven cut

The engine is code, not improvisation: `node "${CLAUDE_PLUGIN_ROOT}/scripts/assemble.js" <command> …` (it uses the Python environment from `/buwan:setup-kit`). Same inputs → same timeline on every editor's machine. Your job is the judgement calls: categories, the story (selects), and reading the results.

**Inputs the editor provides**
- Raw footage folder (read-only). Cameras are the top-level subfolders.
- Music: **track 1 = intro** (the hook, no speech over it) and **track 2 = the story through the outro**. Put them in a `music/` folder next to the footage or in the project; name them `01_*` and `02_*`. One track only → it is track 2 (no separate intro).

## Steps (run in order; each writes to `<project>/edit/assemble/`)
1. **scan** — `assemble.js scan <project> --footage <dir> --music <music dir>` → `clips.json` (ffprobe of every file; nothing is guessed).
2. **cull** — `assemble.js cull <project>` → `cull.json`. Rejects: false starts, black, blown-out, dead. Warnings: dark, soft-focus, heavy-motion, frozen, low-audio. Show the editor the rejected list with reasons; they can un-reject by name (edit `cull.json`, set `reject: []`).
3. **music** — `assemble.js music <project> --intro <track1> --main <track2>` → tempo, beats, bars, energy, sections (soft intro · build · **peak** · release · outro). Tell the editor where the peak is; the kiss will land there.
4. **sync** — `assemble.js sync <project> --anchor "<camera that rolled longest on the ceremony>" --trusted <cameras whose clocks are right>` → `sync.json` + `multicams.json`. Cameras with a wrong clock still sync (it matches sound). Report: how many clips synced by audio, by timestamp, unsynced; multicam groups found.
5. **categorize** — do `/buwan:organize` steps 1–2 (thumbnails + audio → category per clip) and write `edit/assemble/categories.json` as `{ "<absolute clip path>": "<category>" }` using exactly the house category names.
6. **enhance + dead air** — `assemble.js enhance <project> [--render]` → `enhance.json` (per speech clip: loudness, noise floor, SNR, and the enhancement recipe; `--render` also writes cleaned WAVs to `edit/audio/clean/` for Premiere/Resolve). `assemble.js deadair <project>` → `speech_ranges.json`. Report the noisy clips (SNR < 15 dB → use the lav/recorder file) and the minutes of dead air removed.
   Then `assemble.js organize <project> --multicam --event "<event name>"` → `edit/organize_vN.fcpxml`: every clip with its keyword (bin), role, rejected rating, warnings as notes, speech ranges as **Favorites**, plus multicam clips. Editor imports it (**File → Import → XML**).
   Then `assemble.js aroll <project> --event "<event>" [--grade warm]` → `edit/aroll-clean_vN.fcpxml`: the **A-Roll clean** project — every speech clip in sync order with the dead air cut out and the sound enhancement applied. The fastest way to hear the whole day.
7. **Story-Lock** — `/buwan:plot`. Its output is `edit/assemble/selects.json`: ordered lines `{clip, in, out, beat, part, speaker, text, hold?}` (seconds in the source clip). `assemble.js selects <project> --selects … --multicam` → `edit/selects_vN.fcpxml` for review.
8. **build** — `assemble.js build <project> --selects edit/assemble/selects.json --multicam --event "<event>" --name "SDE Cut" --grade <warm|cool|bw> [--fcp-lut] --options '{"title_at":"end","final_hold_s":27}'` → `edit/sde-cut_vN.fcpxml` + `.edl` (picture, for the proof gate) + `.map.png` (edit map) + `.plan.json`. Speech clips carry the enhancement recipe; `--grade` tags the look (`--fcp-lut` writes Final Cut's Custom LUT effect on camera clips — experimental, test on the selftest project first). SDE: `title_at: end` and `final_hold_s: 25–30` (the reference shape); highlight films keep the title on the first hit.
   - **View the edit map** (Read the PNG) and describe the shape to the editor: where the holds are, where the burst sits, whether the kiss is on the peak, how much breathing room was added.
   - Run `/buwan:proof-gate` on the `.edl` (mode cut). Fix and rebuild if it fails.
   - Read the build notes: a WARN means the music and the story don't fit (peak too early, music too short). Options: a different track 2, trim selects, or accept.
9. Editor imports `sde-cut_vN.fcpxml`. It opens as a project: speech on the primary storyline (gaps where the music breathes), b-roll connected above cut on the beats, music on the lanes below (track 1 at −3 dB, track 2 as a −20 dB bed), markers for parts, holds, the music peak, and the graphics to render (`/buwan:graphics` then places the SDE title plate and the logo reveal/end credits).

## How the timeline is built (so you can explain it)
- Track 1: a cold open (~12 s of ~3 s shots: venue, details, drone — no portraits), then b-roll cut on bars, faster as the energy rises. Title plate marker on the first strong hit after 12 s (`title_at: hit`), or the title closes the film (`title_at: end`, SDE).
- Track 2: the Story-Lock spine in order. Breathing room is added at part boundaries so the **kiss (or the climax power statement) lands on the music peak**. Cut rate follows the energy: ~3 s shots when quiet, ~2 s mid, 1–1.2 s in the peak (the burst montage: reactions, ceremony, party). **Vows and first looks are holds** — no cutaways. The speaker stays on camera for the first 3 s of each part. B-roll is chosen by beat: about the bride/groom → prep + portraits, kiss → ceremony + reactions, final wishes → party. Slow-motion (50/59.94 fps) is conformed to 23.976. Outro resolves on the track's tail; logo-reveal marker 4.5 s before the end.
- Options (`--options '{"music_bed_db":-18,"face_s":2}'`): `music_bed_db`, `intro_music_db`, `face_s`, `logo_lead`, `title_after_s`, `cold_open_s` (12), `title_at` (hit|end), `final_hold_s` (0; SDE 25–30 — one shot under the last vow lines).

## Rules
- Never write under the footage root. All outputs go to `<project>/edit/`.
- If the editor's app is Premiere or Resolve: the same FCPXML imports there (Resolve: File → Import → Timeline; Premiere: via the bridge's XML import or Resolve as a bridge). Rejected clips appear as keywords/notes if the app doesn't support ratings.
- Same-day mode: run steps 1–8 straight through; skip thumbnails in step 5 (categorize from folders + audio); the edit map is the review.
- Self-test on a new machine: `assemble.js selftest <folder>` builds a synthetic wedding and must print `SELFTEST PASS`; importing its FCPXML into Final Cut proves the builder on that machine.
