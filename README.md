# Buwan Films — Claude Code plugins

One studio standard for every Buwan editor, in every editing app. Claude Code loads these rules automatically, so each editor's Claude organizes, cuts, grades and brands a film the same way — following the [Edit Pipeline](https://claude.ai/artifact/2dNyL6Us3Ga6KiAvBhtGtq) and the [Video Component Kit](https://claude.ai/artifact/1ZbTbjgoM68B4MZobbsPic) — whether the editor uses Premiere Pro, Final Cut Pro or DaVinci Resolve.

| Plugin | Who installs it | What it adds |
|---|---|---|
| `buwan` | Every editor | House rules, a skill per pipeline stage, shared clip colors and bins, studio LUTs + grade check, brand fonts and logo, kit graphics renderer, proof gate, source protection, app playbooks |
| `buwan-premiere` | Premiere editors only | The Premiere Pro bridge (premiere-pro-mcp 1.11.5) + the apply layer: everything the engine decided, done inside the open Premiere project (`/buwan-premiere:premiere-apply`, `/buwan-premiere:wedding-day`) |

## What happens on a new wedding project
The editor makes the project and places the music. Claude Code does **the basics** and stops:

| | How |
|---|---|
| **Dedupe + working copy** | `assemble.js workcopy`: the raw clips mirrored into `<raw>_WORK/RAW_COPY/` on the same SSD, every file verified by hash, byte-identical duplicates skipped and logged; the project reads only from the copy, originals and copy read-only to Claude |
| **Cull** | unusable clips rejected (false start, black, blown, dead) — flags, never deletions |
| **Categorize** | every clip in one of the 12 studio categories |
| **Dead air** | silences found and removed; speech ranges become subclips / Favorites, the **A-Roll clean** is the whole day's speech back to back; cleaned −17 LUFS WAVs |
| **Label colors** | the same colors in every app (Premiere labels, Final Cut roles, Resolve clip colors); soft / dark / blown / frozen b-roll parked in `00 Flagged/<reason>` |
| **Shaky — Creative/Glider only** | the best cut first (steady stretch → Steady pick); only **gimbal** shots are stabilized — Warp Stabilizer (Premiere) / Stabilization (Final Cut) on their best cut; handheld or too shaky → Flagged. Gimbal = camera folder named Glider/Gimbal/Ronin…, or listed in `edit/assemble/gimbal.txt` / `steady --gimbal` |

On request only: `/buwan:multicam` (sync by audio: vows, interviews, ceremony), `/buwan:plot` (story), the cut, grade, graphics, export.

Pipeline pages, one per app — the editor opens theirs before starting: [**Premiere Pro**](https://claude.ai/artifact/HrCot8tdBvKcsVi26Kyz2A) · [**Final Cut Pro**](https://claude.ai/artifact/KDbKXcPbWxx1QmBHUADYmF) (copies in `plugins/buwan/reference/pipeline-*.html`).

## What every editor gets the same
| | How it's shared |
|---|---|
| **Originals** | `sources/`, `RAW_COPY/` and the original card folders are read-only — Claude can't delete, move or overwrite footage |
| **Grade** | Studio LUTs `Buwan_Warm / Cool / BW.cube` (same file in all three apps) + `/buwan:grade` measures every export against the studio targets |
| **Branding** | Brand fonts and logo installed by `/buwan:setup-kit`; every title, lower third and end card rendered from the kit as ProRes 4444 + alpha by the same renderer |
| **Sound** | Every speech clip measured; levelled, denoised and voice-isolated in the Final Cut XML itself, cleaned WAVs for Premiere/Resolve |
| **Cuts (on request)** | `/buwan:plot` Story-Lock, then the engine builds the timeline to the music — measured by the proof gate |

## Editor setup (once per computer)
Requirements: Claude Code, Node.js 20.19+, Python 3.9+, ffmpeg (Windows `winget install Gyan.FFmpeg`, macOS `brew install ffmpeg`), and read access to this repository. For transcription: whisper.cpp (`brew install whisper-cpp`; Claude installs the model on first use).

1. Start Claude Code in your Buwan workspace folder (it has `projects/`).
2. Install:
   ```
   /plugin marketplace add Buwan-Films/buwan-claude
   /plugin install buwan@buwan-films
   ```
   Choose your editing app and type your name when asked.
3. Premiere editors only: `/plugin install buwan-premiere@buwan-films`, then with Premiere closed: `npx -y premiere-pro-mcp@1.11.5 --install-cep`.
4. Restart Claude Code, run `/buwan:setup-kit` (fonts, logo, LUTs, renderer, kit clips — about 5 minutes), restart your editing app.
5. Run `/buwan:check`. Everything must pass before client work.

## Getting updates
```
/plugin marketplace update buwan-films
```
Restart Claude Code. If the CHANGELOG mentions kit changes, run `/buwan:setup-kit` again.

## The pipeline, one skill per stage
| Stage | Skill |
|---|---|
| New wedding project — **the basics** | `/buwan:basics` (Premiere: `/buwan-premiere:wedding-day`) |
| 01 Intake (part of the basics) | `/buwan:intake --work-copy` |
| Multicam · on request | `/buwan:multicam` |
| 02 Story-Lock · on request | `/buwan:plot` |
| 02 Rough cut · on request | `/buwan:rough-cut` → `assemble build` (music-driven timeline + edit map) |
| Proof gate | `/buwan:proof-gate` (also automatic on every EDL) |
| 03 Audio | `/buwan:audio` |
| 04 Grade | `/buwan:grade` |
| 05 Graphics + captions | `/buwan:graphics` |
| 06 SFX | `/buwan:sfx` |
| 07 Review | `/buwan:review` |
| 08 Export | `/buwan:export`, then `/buwan:clipper` for reels |
| Same-day edit, the full flow | `/buwan:sde` |
| Engine reference | `/buwan:assemble` |

Example: `/buwan:intake 2026-11-15_Santos-Reyes wedding E:\Cards\Santos-Reyes`

### Premiere Pro, wedding day
`/buwan-premiere:wedding-day 2026-11-15_Santos-Reyes --footage /Volumes/<SSD>/<raw folder>` — with the project already made and the music placed, the engine makes the working copy, culls, categorizes, cuts the dead air and judges the shaky creative shots; the bridge then builds the bins with label colors, the speech subclips, the A-Roll clean, the Steady picks and the STABILIZE sequence in the open project, and writes `EDITOR_START_HERE.md`. Then it stops. `--new-clips` when the shooters hand over more cards. `/buwan:multicam` when you want the vows or an interview synced.

### The music-driven SDE in one line
Put the footage and a `music/` folder (`01_intro.wav`, `02_story.wav`) next to each other, then: `/buwan:sde <project>`. The engine culls, syncs the cameras, organizes, and — after you approve the Story-Lock — builds the timeline cut to your music, with the kiss on the music's peak. Import the FCPXML and refine.
