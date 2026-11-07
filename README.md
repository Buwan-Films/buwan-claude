# Buwan Films — Claude Code plugins

One studio standard for every Buwan editor, in every editing app. Claude Code loads these rules automatically, so each editor's Claude organizes, cuts, grades and brands a film the same way — following the [Edit Pipeline](https://claude.ai/artifact/2dNyL6Us3Ga6KiAvBhtGtq) and the [Video Component Kit](https://claude.ai/artifact/1ZbTbjgoM68B4MZobbsPic) — whether the editor uses Premiere Pro, Final Cut Pro or DaVinci Resolve.

| Plugin | Who installs it | What it adds |
|---|---|---|
| `buwan` | Every editor | House rules, a skill per pipeline stage, shared clip colors and bins, studio LUTs + grade check, brand fonts and logo, kit graphics renderer, proof gate, source protection, app playbooks |
| `buwan-premiere` | Premiere editors only | The Premiere Pro bridge (premiere-pro-mcp 1.11.5) + the apply layer: everything the engine decided, done inside the open Premiere project (`/buwan-premiere:premiere-apply`, `/buwan-premiere:wedding-day`) |

## What every editor gets the same
| | How it's shared |
|---|---|
| **Organize** | `/buwan:intake` folders + `/buwan:organize`: same clip categories, bins and colors (Premiere labels, Resolve clip colors, Final Cut roles) |
| **Footage prep** | `/buwan:assemble`: culls unusable clips, syncs every camera by sound (multicam, even with a wrong clock), analyses the two music tracks — all on the editor's machine, nothing uploaded |
| **Cuts** | `/buwan:plot` Story-Lock, then the engine builds the timeline to the music (cuts on beats, burst on the peak, kiss on the peak, holds clean) — measured by the proof gate |
| **Grade** | Studio LUTs `Buwan_Warm / Cool / BW.cube` (same file in all three apps) + `/buwan:grade` measures every export against the studio targets |
| **Branding** | Brand fonts and logo installed by `/buwan:setup-kit`; every title, lower third and end card rendered from the kit as ProRes 4444 + alpha by the same renderer |
| **Sound** | Every speech clip measured; levelled, denoised and voice-isolated in the Final Cut XML itself, cleaned WAVs for Premiere/Resolve |
| **Dead air** | Silences found and removed: speech ranges become Favorites, and the A-Roll clean project is the whole day's speech back to back |
| **Originals** | `sources/` is read-only — Claude can't delete, move or overwrite footage |

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
| 01 Intake | `/buwan:intake`, then `/buwan:organize` |
| 02 Story-Lock | `/buwan:plot` |
| Prep | `/buwan:assemble` (scan · cull · music · sync · organize · enhance · dead air · A-Roll clean) |
| 02 Rough cut | `/buwan:rough-cut` → `assemble build` (music-driven timeline + edit map) |
| Proof gate | `/buwan:proof-gate` (also automatic on every EDL) |
| 03 Audio | `/buwan:audio` |
| 04 Grade | `/buwan:grade` |
| 05 Graphics + captions | `/buwan:graphics` |
| 06 SFX | `/buwan:sfx` |
| 07 Review | `/buwan:review` |
| 08 Export | `/buwan:export`, then `/buwan:clipper` for reels |
| Same-day edit | `/buwan:sde` |

Example: `/buwan:intake 2026-11-15_Santos-Reyes wedding E:\Cards\Santos-Reyes`

### Premiere Pro, wedding day
The editor's guide (prompts, phases, what stays creative): [Wedding Day in Premiere](https://claude.ai/artifact/QFZtScv62QduRx7CXumHXx).

`/buwan-premiere:wedding-day <project> --footage <dir> --music <dir> --grade warm` — the engine culls, syncs and measures; the bridge then builds the bins with label colors, the dead-air subclips, the A-Roll clean and SYNC sequences in the open project. After the Story-Lock: the SDE Cut as a sequence, graded and leveled. `--new-clips` when the shooters hand over more cards.

### The music-driven SDE in one line
Put the footage and a `music/` folder (`01_intro.wav`, `02_story.wav`) next to each other, then: `/buwan:sde <project>`. The engine culls, syncs the cameras, organizes, and — after you approve the Story-Lock — builds the timeline cut to your music, with the kiss on the music's peak. Import the FCPXML and refine.
