---
name: resolve
description: Buwan app playbook for DaVinci Resolve (free and Studio) — importing Story-Lock EDL/FCPXML, Fairlight loudness, color page grade, captions and Deliver presets, plus optional Studio scripting. Use whenever the editor cuts in DaVinci Resolve or asks for Resolve steps.
---

# App playbook — DaVinci Resolve

House rules come first (`/buwan:house-rules`). Default workflow is file round-trips (works in free and Studio).

## Project setup
- Project settings: timeline 23.976, 1920×1080 (or UHD), playback 23.976. **Output blanking** 2.39:1 or 2.00 via **Timeline → Output Blanking** for the letterbox.
- Media Pool: add `sources/` folders with **Add Folder** (media stays in place). Cache and gallery stills in `edit/`.
- Transcription (Studio 18.5+): right-click clips → **Audio Transcription → Transcribe**; export SRT to `edit/transcripts/`.

## Importing Story-Lock outputs
- EDL: **File → Import → Timeline…** → `selects_vN.edl` → uncheck "Automatically import source clips", let it link from the Media Pool. Name the timeline `Rough Cut vN`.
- FCPXML also works: same menu.
- Captions: **File → Import → Subtitle** → the SRT → drag onto a subtitle track; style with brand fonts.

## 03 Audio (Fairlight)
- Dialogue bus loudness: **Fairlight → Loudness meter** set to −17 LUFS target; **Normalize Audio Levels** on dialogue clips (ITU-R BS.1770, −17 LUFS, true peak −6 dBTP). Limiter on the dialogue bus at −6 dB.
- Music bed at −20 dB clip gain, flat.

## 04 Grade (Color page)
- Node tree: Input (CST/LUT from `kit/luts/`) → Balance → Look → Output. Shared nodes or groups per scene. Camera clips only.

## 05 Graphics
- Kit clips from `kit/` on upper tracks; Text+ titles use brand fonts and hex codes. Grain via Film Grain (Studio) at 5–6% or the kit grain overlay.

## Proof gate export
- **File → Export → Timeline… → EDL** (V1 only) → `edit/cut_vN.edl` → `/buwan:proof-gate` mode cut.

## 08 Deliver
- Master: **Deliver → YouTube** preset adjusted to source frame rate, H.264/H.265, 20–50 Mbps. Reels: duplicate timeline at 1080×1920, **Smart Reframe** (Studio) or manual reposition, then render.

## Optional: Studio scripting
Resolve **Studio** exposes a Python scripting API (`DaVinciResolveScript`), enabled in **Preferences → System → General → External scripting using: Local**. Only use it when the editor asks and confirms Studio; build into new timelines only, never modify existing ones. The free version cannot be scripted externally — use file round-trips.
