# Changelog

## buwan 1.1.1 · buwan-premiere 1.0.1 — 2026-11-05
- Repo moved to the Buwan-Films org: install with `/plugin marketplace add Buwan-Films/buwan-claude`.

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
