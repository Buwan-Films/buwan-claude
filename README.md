# Buwan Films — Claude Code plugins

One set of editing rules for every Buwan editor, in every editing app. Claude Code loads these rules automatically, so each editor's Claude follows the [Edit Pipeline](https://claude.ai/artifact/2dNyL6Us3Ga6KiAvBhtGtq) and the [Video Component Kit](https://claude.ai/artifact/1ZbTbjgoM68B4MZobbsPic) without being told.

| Plugin | Who installs it | What it adds |
|---|---|---|
| `buwan` | Every editor | House rules, app playbooks (Premiere, Final Cut, Resolve), `/buwan:intake`, `/buwan:plot`, `/buwan:proof-gate`, `/buwan:export`, `/buwan:check`, source protection, automatic proof gate on EDLs |
| `buwan-premiere` | Premiere editors only | The Premiere Pro bridge (premiere-pro-mcp 1.11.5) |

## Editor setup (once per computer)

Requirements: Claude Code, Node.js 20.19+ (`node --version`), ffmpeg, GitHub access to this repository, and the brand fonts (Cormorant Garamond, Cinzel, Italiana).

1. Start Claude Code in your Buwan workspace folder (it has `projects/` and `kit/`).
2. Add the marketplace and install:
   ```
   /plugin marketplace add buwanfilms-svg/buwan-claude
   /plugin install buwan@buwan-films
   ```
   When asked, choose your editing app and type your name.
3. Premiere editors only:
   ```
   /plugin install buwan-premiere@buwan-films
   ```
   Then, with Premiere closed, install the panel once: `npx -y premiere-pro-mcp@1.11.5 --install-cep`.
4. Restart Claude Code and run `/buwan:check`. Every item must pass before client work.

## Getting updates
```
/plugin marketplace update buwan-films
```
Then restart Claude Code. `/buwan:check` shows the version you're on.

## Daily use
| Stage | Say |
|---|---|
| 01 Intake | `/buwan:intake 2026-11-15_Santos-Reyes wedding E:\Cards\Santos-Reyes` |
| 02 Story-Lock | `/buwan:plot projects\2026-11-15_Santos-Reyes_wedding highlights 7min` |
| Proof gate | `/buwan:proof-gate edit\cut_v1.edl` (also runs automatically when Claude writes an EDL) |
| 08 Export | `/buwan:export` |

Add "same-day mode" for SDEs.
