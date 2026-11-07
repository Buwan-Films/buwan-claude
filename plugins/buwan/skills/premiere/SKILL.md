---
name: premiere
description: Buwan app playbook for Adobe Premiere Pro (the studio default) — importing Story-Lock outputs, driving Premiere through the MCP bridge, audio, grade, captions and export presets. Use whenever the editor cuts in Premiere Pro or asks for Premiere steps.
---

# App playbook — Premiere Pro

House rules come first (`/buwan:house-rules`). This file is only the "how" in Premiere.

## The basics, applied by code (buwan-premiere plugin)
Organize → color → grade → sound → cull → dead air → sync → the SDE Cut are not done by hand in Premiere: the engine decides (`/buwan:assemble`), `assemble.js premiere <project>` writes `edit/premiere/manifest.json`, and `/buwan-premiere:premiere-apply` applies it in the open project through the bridge (bins + label colors, `00 Rejected (cull)`, speech-range subclips, A-Roll clean, SYNC sequences, the plan as a sequence, Lumetri + studio LUT, measured gain + DeNoise + limiter). On a wedding day run `/buwan-premiere:wedding-day`. Hand steps below are for what the apply layer reports it could not do.

## Live bridge (buwan-premiere plugin)
- Before any timeline work: run "Verify Premiere connection". Needs Premiere open, a project open, an active sequence, and **Window → Extensions → MCP Bridge** showing the connector running.
- On client projects, never edit the editor's working sequence in place. Duplicate it, or build into a NEW sequence (`Rough Cut v<N>`, `Picture Lock v<N>`), and tell the editor which one.
- Never delete project items, relink media away from `sources/`, or consolidate/trim media. Save the project (`Ctrl+S` equivalent through the bridge) after each batch of changes and say so.
- If a bridge call fails twice, stop and fall back to file import (EDL/XML) — don't loop on it.

## Project setup
- Project file lives in `edit/`: `<project>_v<N>.prproj`. Scratch disks and auto-save to `edit/`.
- Sequence: 23.976 fps, 1920×1080 (or UHD), 48 kHz. Letterbox 2:1 / 2.39:1 with a kit letterbox clip on the top video track, not by changing the sequence frame size.
- Speech clips: **Automatic transcription** on import (Language: Filipino if Tagalog dominates, else English). Export transcripts via **Text panel → … → Export to text/SRT** into `edit/transcripts/`.

## Importing Story-Lock outputs (no bridge)
- EDL: **File → Import** → `selects_vN.edl` → 23.976 → it creates a sequence; relink offline clips to `sources/` if prompted (Locate, don't copy).
- Captions: **File → Import** the SRT, drag to the timeline as a caption track; apply the kit caption style.

## 03 Audio
- Dialogue to −17 LUFS: **Essential Sound → Dialogue → Loudness → Auto-Match** (target set in Preferences → Audio to −17 LUFS), then a **Hard Limiter** on the dialogue submix at −6 dB.
- Music bed: Essential Sound → Music → clip volume to −20 dB flat (no ducking unless the editor asks).
- Verify with **Window → Loudness Radar** or by measuring the export.

## 04 Grade
- Studio LUT per camera clip via the apply layer (`grade` step: Lumetri Creative → Look, 80%); by hand: Lumetri on an **adjustment layer** per scene with the same `kit/luts/Buwan_*.cube`. Camera clips only. B&W only for the most intimate beats.

## 05 Graphics + captions
- Kit clips from `kit/` on upper tracks. Text built in Premiere uses the brand fonts and hex codes only. Grain overlay 5–6% on graphic frames.
- After Effects only for components that need to be rebuilt; Dynamic Link from `edit/`.

## Proof gate export
- **File → Export → EDL** → CMX3600, 23.976, video track V1 only (picture cut) → `edit/cut_vN.edl`, then `/buwan:proof-gate`.

## 08 Export presets
- Master: **Export → H.264 → Match Source – High Bitrate**, VBR 2-pass, target 20 Mbps (1080p) / 50 Mbps (UHD), AAC 320 kbps.
- Reels: duplicate sequence → **Sequence → Auto Reframe Sequence** to 9:16 → check every shot → export 1080×1920.
- Files go to `exports/`.
