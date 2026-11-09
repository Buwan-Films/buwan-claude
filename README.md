# Buwan Films — Claude Code plugins

One studio standard for every Buwan editor, in every editing app. Claude Code loads these rules automatically, so each editor's Claude organizes, cuts, grades and brands a film the same way — following the [Edit Pipeline](https://claude.ai/artifact/2dNyL6Us3Ga6KiAvBhtGtq) and the [Video Component Kit](https://claude.ai/artifact/1ZbTbjgoM68B4MZobbsPic) — whether the editor uses Premiere Pro, Final Cut Pro or DaVinci Resolve.

| Plugin | Who installs it | What it adds |
|---|---|---|
| `buwan` | Every editor | House rules, a skill per pipeline stage, shared clip colors and bins, studio LUTs + grade check, brand fonts and logo, kit graphics renderer, proof gate, source protection, app playbooks |
| `buwan-premiere` | Premiere editors only | The Premiere Pro bridge (premiere-pro-mcp 1.11.5) + the apply layer: everything the engine decided, done inside the open Premiere project (`/buwan-premiere:premiere-apply`, `/buwan-premiere:wedding-day`) |

## What happens on a new wedding project
Claude Code makes **enhanced clips** from the raw footage and stops. The raw folder is only read; every run writes a new folder next to it, `<raw>_ENHANCED_<date-time>/`, with the same camera/card folders and clip names (HEVC 10-bit `.mov`). No copying, no dedupe, no file organizing, **no grade**.

| | How |
|---|---|
| **Exposure on every clip** | `assemble.js exposure`: a gentle per-clip fix toward the studio brightness band (±1.5 EV max, highlights protected, low-key shots left alone) |
| **Shaky — Creative/Glider only** | the best cut of each shaky clip, then a smooth glide (vid.stab). Other cameras untouched |

`assemble.js render` writes it all. Then, when the editor asks:

| Skill | What it makes |
|---|---|
| `/buwan:multicam` — interviews, vows, speeches | the editor lists a moment's clips → the best audio picked, the angles synced to it by sound, cleaned to −17 LUFS / peaks −6, the dead air cut at the same points on every angle, each angle rendered with its exposure fixed → `<raw>_SPEECH_<date-time>/INTERVIEWS\|VOWS\|SPEECHES/<moment>/`, ready for a multicam |
| `/buwan:grade` — the look | a LUT built from the studio's own film (`assemble.js look --reference <film>`, before/after sheet) or the stock studio LUTs, applied in the editing app |

Also on request: `/buwan:plot` (story), the cut, Premiere bins and labels (`/buwan-premiere:premiere-apply`), graphics, export.

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
| Interviews / vows / speeches · on request | `/buwan:multicam` (angles synced on the best audio, dead air out → `<raw>_SPEECH_*/`) |
| Grade · on request | `/buwan:grade` (the look, in the app) |
| 02 Story-Lock · on request | `/buwan:plot` |
| 02 Rough cut · on request | `/buwan:rough-cut` → `assemble build` (music-driven timeline + edit map) |
| Proof gate | `/buwan:proof-gate` (also automatic on every EDL) |
| 03 Audio | `/buwan:audio` |
| 04 Grade | `/buwan:grade` |
| 05 Graphics + captions | `/buwan:graphics` |
| 06 SFX | `/buwan:sfx` |
| 07 Review | `/buwan:review` |
| Couple's names | `/buwan:title "Mary Nhor and Jomar"` (kit 07.09: The Wedding of · the names wide-tracked · Buwan Films, over the last wide shot) |
| Logo end card | `/buwan:end-card` (kit 06.08: two blades become one ring, the emblem lands, last shot of every film) |
| 08 Export | `/buwan:export`, then `/buwan:clipper` for reels |
| Same-day edit, the full flow | `/buwan:sde` |
| Engine reference | `/buwan:assemble` |

Example: `/buwan:intake 2026-11-15_Santos-Reyes wedding E:\Cards\Santos-Reyes`

### Premiere Pro, wedding day
`/buwan-premiere:wedding-day 2026-11-15_Santos-Reyes --footage /Volumes/<SSD>/<raw folder>` — with the project already made and the music placed, the engine makes the working copy, culls, categorizes, cuts the dead air and judges the shaky creative shots; the bridge then builds the bins with label colors, the speech subclips, the A-Roll clean, the Steady picks and the STABILIZE sequence in the open project, and writes `EDITOR_START_HERE.md`. Then it stops. `--new-clips` when the shooters hand over more cards. `/buwan:multicam` when you want the vows or an interview synced.

### The music-driven SDE in one line
Put the footage and a `music/` folder (`01_intro.wav`, `02_story.wav`) next to each other, then: `/buwan:sde <project>`. The engine culls, syncs the cameras, organizes, and — after you approve the Story-Lock — builds the timeline cut to your music, with the kiss on the music's peak. Import the FCPXML and refine.
