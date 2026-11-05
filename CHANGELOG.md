# Changelog

## buwan 1.2.0 · buwan-premiere 1.0.1 — 2026-11-06  (run /buwan:setup-kit: installs the Python engine)
- **Assemble engine** (`/buwan:assemble`): scan (ffprobe everything) · cull (false starts, black/blown, dark, soft-focus, heavy motion, dead audio — flags, never deletes) · music analysis of the two tracks (tempo, beats, bars, energy, peak/outro sections) · multicam sync by audio cross-correlation (cameras with a wrong clock still sync) · deterministic FCPXML builder validated against Apple's FCPXML 1.11 DTD (organize with bins/roles/rejects/multicam, Story-Lock selects, and the music-driven cut) · picture EDL for the proof gate · edit-map PNG.
- Music-driven timeline: track 1 = intro (b-roll on bars, title-plate marker on the first hit), track 2 = story (speech spine, breathing room so the kiss lands on the music peak, cut rate follows energy, burst montage on the peak, vows/first looks held clean, speaker on camera for the opening of each part, slow motion conformed, logo-reveal marker before the end).
- organize / plot / rough-cut / sde / final-cut skills now route through the engine instead of hand-written XML. Final Cut tcStart fixed to exactly 01:00:00:00 (86486400/24000s).
- setup-kit: creates `~/.buwan/venv` (numpy, scipy, librosa, soundfile, pillow) and fetches the FCPXML DTD; `scripts/assemble.js` launcher.
- Repo moved to the Buwan-Films organization (1.1.1).

## buwan 1.1.0 — 2026-11-04  (kit changes: run /buwan:setup-kit)
- A skill for every stage: organize, rough-cut, audio, grade, graphics, sfx, review, clipper, sde, setup-kit (plus intake, plot, proof-gate, export, check).
- Shared clip categories, bins and colors for Premiere (labels), Resolve (clip colors) and Final Cut (roles).
- Brand fonts (Cormorant Garamond, Cinzel, Italiana — SIL OFL) and logo files, installed by /buwan:setup-kit.
- Kit renderer: any Video Kit component rendered with real names/dates as ProRes 4444 + alpha, 23.976 — identical in every app. Reusable clips (logo, watermark, letterbox, moonrise/wipe mattes, light leak) rendered at setup.
- Starting studio looks Buwan_Warm/Cool/BW.cube and the grade check (black/white levels, brightness, saturation, hue) with calibration from reference stills.

## buwan 1.0.0 · buwan-premiere 1.0.0 — 2026-11-04
- First release: house rules from the Edit Pipeline and Video Component Kit, Premiere / Final Cut / Resolve playbooks, intake, plot (Story-Lock), proof gate, export and setup-check skills.
- Hooks: rule card at session start, read-only `sources/`, automatic proof gate whenever an EDL is written.
- Premiere bridge pinned to premiere-pro-mcp 1.11.5.
