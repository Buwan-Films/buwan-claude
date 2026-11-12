---
name: premiere-apply
description: Apply the Buwan assemble engine's decisions inside Adobe Premiere Pro through the bridge — import into the studio bins with label colors, cull, speech subclips with dead air removed, the A-Roll clean sequence, stacked SYNC sequences per multicam group, the music-driven SDE timeline from the plan, studio LUT on every camera clip, measured dialogue gain + DeNoise + limiter. Use when an editor in Premiere says organize/color/grade/enhance/cull/dead air/sync/build "in Premiere", "do it in the project", or after /buwan:assemble on a Premiere job.
argument-hint: "<step|all> <project folder> [opts]"
---

# Premiere apply — the engine's decisions, done in the open project

Everything the editor sees in Premiere (bins, label colors, subclips, sequences, effects) comes from `<project>/edit/premiere/manifest.json`, written by the engine, and applied by the ExtendScript library `jsx/buwan.jsx` through the bridge's `execute_extendscript`. Same manifest → same project on every editor's machine. Nothing is deleted, renamed or re-encoded; every step is additive and undoable (Edit → Undo).

## Before the first step
1. The basics must have run (`workcopy`, `scan`, `cull`, `categories.json`, `enhance --render`, `deadair`, `steady` — `/buwan:basics`). `sync` only after `/buwan:multicam`; `build` (plan) only when the Story-Lock is approved.
2. Write the manifest (re-run it whenever the engine outputs change):
   `node "<buwan plugin>/scripts/assemble.js" premiere <project> --grade <warm|cool|bw> [--plan <project>/edit/sde-cut_vN.plan.json] [--use-clean] [--no-flags]`
   (`--use-clean` lays the cleaned −17 LUFS WAVs under each speech clip when building, muting the camera audio. `--no-flags` keeps shaky/soft/dark clips in their category bins.)
3. Premiere open, **the job's project open** (`edit/<project>_v<N>.prproj`), **Window → Extensions → MCP Bridge** running. Run "Verify Premiere connection" (`get_full_project_overview` or `get_project_info`). If it fails twice, stop and tell the editor — don't loop.

## Running a step
Get the exact code with `node "${CLAUDE_PLUGIN_ROOT}/scripts/premiere-snippet.js" <step> "<project>/edit/premiere/manifest.json" ["{opt:value}"]` and pass it verbatim to **`execute_extendscript`** with the printed `timeout_ms`. The code is one line:
```
$.evalFile(new File("<plugin>/jsx/buwan.jsx")); return __result(BUWAN.run("<step>", "<manifest>", "{...opts}"));
```
Read the returned object: `ok`, counts, `failed_clips`, `hint`, `log`. Report counts to the editor in one line per step. A `hint` is an instruction for you (run again, import first, etc.).

| Step | What it does in Premiere | Opts |
|---|---|---|
| `enhanced` | **The basics' `_ENHANCED_` folder** (manifest `edit/premiere/enhanced.json` from `assemble.js premiere-import <project>`, not manifest.json): imports every enhanced clip not in the project into `ENHANCED <date-time>/<camera>`, 300 per call — repeat while `remaining > 0`. Drone cameras Teal; clips with speech (from `transcripts.json`) Mango + "<vows/mass/speech/talk>: first words" in Description; smoothed Creative clips "smoothed (best cut)". Clips already in the project only get label + Description when theirs is still empty (the editor's changes are kept). No sequences | `{limit:300, srt:true}` also imports the speech clips' SRTs into `ENHANCED …/Transcripts` |
| `status` | Manifest vs project: clips not imported yet, clips in the project the engine hasn't seen (new footage from the shooters) | |
| `import` | Imports missing clips straight into their category bins (and `01 Speech/Clean audio` with `--use-clean`). 150 files per call — repeat while `remaining > 0` | `{limit:150}` |
| `organize` | Moves every clip to its category bin (`01 Speech` … `12 Grade & Adjust`; prep clips into `02 Prep & Details/Bride prep` · `Groom prep` from `subbins.json`) and sets the **house label color** (Speech Mango, Prep Tan, Portraits Yellow, Ceremony Violet, Reactions Rose, Establishing Cerulean, Reception Magenta, Drone Teal, Music Forest, SFX Caribbean, Graphics Lavender, Adjust Brown). Rejects → `00 Rejected (cull)`, Brown. **Flagged** b-roll (heavy motion, soft focus, dark, blown, frozen — never speech) → `00 Flagged/<reason>`, category label kept, reason in Description | `{flag_warnings:false}` keeps them in their category bins |
| `cull` | Only the rejects, with reasons (false-start, black, blown, silent-dead) | |
| `deadair` | One **subclip per speech range** (silences cut) into `01 Speech/Speech ranges`, named `<clip> - speech NN [mm:ss-mm:ss]` | `{limit:400}` |
| `aroll` | Sequence **A-Roll clean**: every speech range back to back (0.3 s gap), a marker per clip — the whole day's speech to listen through | `{name:"A-Roll clean", gap:0.3}` |
| `sync` | One **SYNC <group>** sequence per multicam group, each camera on its own V/A track at its audio-sync offset (clocks don't matter). Editor then: Project panel → right-click the SYNC sequence → **Multi-Camera → Enable** | `{group:"mc1"}` |
| `steady` | Shaky **Creative/Glider** clips only: best cut first: steady stretch → subclip in `<category>/Steady picks` (label kept), no stabilizing; **gimbal shots only** with no steady stretch → their best cut placed in the **STABILIZE – Warp** sequence with Warp Stabilizer applied; handheld or too shaky → stays in `00 Flagged/Heavy motion`, not stabilized | `{name:"STABILIZE - Warp"}` |
| `skeleton` | (Only when asked.) An empty assembly sequence `SDE_ASSEMBLY_v1` (23.976, 1920×1080, TC 01:00:00:00, 3V/3A): V1 empty, purple section markers INTRO · STORYLINE · CEREMONY · OUTRO over the 4–5 min target, red TARGETS marker (−17 LUFS, −6 dBFS, bed −20 dB), story track on A3 at −20 dB as a placeholder bed, orange markers for the two hand steps (adjustment layer + look on V2, letterbox on V3) | `{name:"SDE_ASSEMBLY_v1"}` |
| `relink` | Points every project item at its `BY_CATEGORY/` clone (`assemble.js bycategory`); same bytes, so subclips and sequence clips are unaffected. Clips trimmed to their best cut stay on `RAW_COPY/`. 150 per call — repeat with `{start: next_start}` while `remaining > 0` | `{start, limit}` |
| `basics` | import → organize → deadair → aroll → steady → relink → grade (A-Roll clean, STABILIZE only), then **stops**. No sync, no sequence to cut in, no build, no grading of the editor's sequences — the same-day scope (`/buwan:basics`) | |
| `build` | The plan's timeline as a new sequence (23.976, 1920×1080, TC 01:00:00:00): speech on **V1/A1**, b-roll on **V2** cut on the beats, music 1 on A2/A3 (−3 dB), music 2 as the −20 dB bed, chapter markers per part (purple), red = music peak / final hold, orange = graphics TODO. Slow-mo b-roll is **interpreted** to 23.976 (Modify → Interpret Footage) | `{name:"SDE Cut", preset:"<path>.sqpreset"}` |
| `grade` | **Lumetri Color** on every camera clip of the sequence (active, or `{sequence:"name"}`) with the per-clip **Exposure** fix from `exposure.json`; music, SFX, graphics, adjustment clips skipped. The look: Premiere 26.x won't take a LUT from a script (a file path is refused; a list position doesn't load a user LUT), so the script sets Lumetri and the Exposure fix, and the editor picks **Creative → Look → Buwan_Warm** once on one clip; `grade {look_from:"<sequence>/<clip index>"}` then copies it to the rest (being verified). The Buwan LUTs appear in that list after `/buwan:setup-kit` and a Premiere restart. Batches of 200: `{start, limit}` | `{sequence:"SDE Cut", start:0, limit:200, look_from:"SDE Cut/0"}` |
| `enhance` | Speech clips of the sequence: measured **gain** (toward −17 LUFS), **DeNoise** (amount from the clip's SNR), **Hard Limiter** −6 dB. Verify with Essential Sound → Loudness → Auto-Match and the Loudness Radar | `{sequence:"SDE Cut"}` |
| `all` | import → organize → deadair → aroll → sync → (build → grade → enhance when the manifest has a plan) | |

Premiere's scripting API cannot: change clip speed (hence Interpret Footage), create a true multicam source sequence (hence SYNC + Enable), or always keep effect-property writes on some 26.3 builds — the steps read values back and list what failed under `failed_clips`; tell the editor exactly which clips to finish by hand.

## After the steps — what the editor does by hand
Creative decisions only: watch the SDE Cut with the edit map (`edit/sde-cut_vN.map.png`), swap b-roll choices, nudge the holds, confirm the kiss sits on the peak, set the two speed ramps if any, place the kit graphics on the orange markers (`/buwan:graphics`), SFX (`/buwan:sfx`), then `/buwan:review` and `/buwan:export`.

## New clips from the shooters
Drop them into the same footage folder (new camera folder or existing one), then: `assemble.js scan` → `cull` → `sync` (same anchor) → categories for the new paths → `enhance --render` → `deadair` → `assemble.js premiere …` → bridge `status` (shows them as not imported) → `import` → `organize` → `deadair`. Existing bins, labels, subclips and sequences are left as they are; only the new clips are added. Rebuild the SDE Cut only if the Story-Lock changes (new sequence `SDE Cut v2`, never over the editor's working sequence).
