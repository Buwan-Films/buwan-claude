---
name: final-cut
description: Buwan app playbook for Final Cut Pro on macOS — FCPXML round-trips for Story-Lock outputs, roles, audio, grade, captions and share presets. Use whenever the editor cuts in Final Cut Pro or asks for FCP steps.
---

# App playbook — Final Cut Pro

House rules come first (`/buwan:house-rules`). Final Cut has no live bridge: Claude writes FCPXML and the editor imports it. Final Cut does NOT import EDL — always deliver FCPXML to FCP editors.

## Writing FCPXML (Story-Lock and recuts)
**Use the engine, not hand-written XML:** `node "${CLAUDE_PLUGIN_ROOT}/scripts/assemble.js" organize|selects|build …` (see `/buwan:assemble`). It probes every file, writes correct formats/frame rates/paths, conforms slow motion, builds multicam clips, and validates against Apple's DTD. The notes below describe what it writes, for when you need to read or debug a file.
- Version: `<fcpxml version="1.11">` (FCP 10.7+).
- Probe every referenced source with `ffprobe -v error -show_streams -show_format -of json <file>` to get duration, frame rate, resolution and audio channels. Never guess media metadata.
- Resources: one `<format>` per distinct source format (23.976 = `frameDuration="1001/24000s"`), one `<asset>` per source file with `<media-rep kind="original-media" src="file:///...">` pointing into `sources/` (URL-encode spaces).
- Timeline: `<event>` → `<project>` → `<sequence format=… tcStart="86486400/24000s" tcFormat="NDF">` (that is exactly 01:00:00:00 at 23.976; `3600/1s` would read 00:59:56:10) → `<spine>` of `<asset-clip>`/`<mc-clip>` in story order. Times are rational seconds on the 1001/24000 grid. Slow motion: `<conform-rate scaleEnabled="1" srcFrameRate="59.94"/>` with start/duration in **source** time.
- Markers: `<marker>` at each part boundary (Intro / Storyline / Ceremony / Outro) and on hold points.
- Save as `edit/selects_vN.fcpxml` and also give the editor the SRT.
- Self-check before handing over: well-formed XML (`xmllint --noout` if available), every `ref` resolves to a resource, every asset path exists, all times on the frame grid.

## Import
- **File → Import → XML…** → choose the `.fcpxml` → pick or create the library in `edit/`. Media stays in place ("Leave files in place"); never copy into the library.
- Captions: **File → Import → Captions** → the SRT → set role to SRT; apply kit caption style.

## Library settings
- Library in `edit/<project>.fcpbundle`, media **external** (leave in place), cache in `edit/`.
- Roles: Dialogue (subroles per speaker), Music, Effects, Titles.

## 03 Audio
- Dialogue to −17 LUFS: Loudness effect / Logic Adaptive Limiter on the Dialogue role (compound or role output), ceiling −6 dB. Music role at −20 dB flat.
- Verify by measuring the share with ffmpeg ebur128.

## 04 Grade
- Color Board / Color Wheels on adjustment-layer titles or per clip; saved looks from `kit/luts/` via **Custom LUT**. Camera clips only.

## Proof gate export
- **File → Export XML…** of the picture-locked project → Claude converts the primary storyline to a CMX3600-equivalent cut list and runs `/buwan:proof-gate` (mode cut). Count spine clips only, not connected clips, unless the editor says the b-roll is connected.

## 08 Share
- Master: **File → Share → Master File** → H.264 or HEVC, source frame rate. Reels: duplicate project → **Modify → Smart Conform** at 9:16 → check each shot → share 1080×1920.
