---
name: export
description: Pipeline stage 08 — export Buwan deliverables per platform (YouTube master, 9:16 reels, corporate 16:9 recap and 1:1 LinkedIn) and the pre-export checklist. Use when an editor says export, render, deliver, master, reels, or Clipper.
argument-hint: "[project folder]"
---

# 08 Export

Follow the house rules and the editor's app playbook for the exact preset steps.

## Before export (all must be true)
- Proof gate passed (or override written in the paper edit).
- Dialogue −17 LUFS integrated, true peak ≤ −6 dBFS; music bed −20 dB. Measure the export with `ffmpeg -i <file> -af ebur128=peak=true -f null -` and report the numbers.
- Proper nouns in captions spot-checked by the editor.
- Graphics are kit components only; Italiana appears only in weddings.

## Deliverables
| Shoot | File | Spec |
|---|---|---|
| Wedding | YouTube long-form master | H.264 or H.265, source frame rate (23.976), 1920×1080 or 3840×2160 with 2:1/2.39:1 letterbox baked in, AAC 320 kbps 48 kHz |
| Wedding | Clipper 9:16 reels | 1080×1920, ≤ 90s each, hook in first 3s, burned-in captions (kit caption style), re-enter pipeline at 01 |
| Corporate | 16:9 recap | 1920×1080, H.264, AAC 320 kbps |
| Corporate | 1:1 LinkedIn cut | 1080×1080, H.264, captions burned in |
| Corporate | Clipper 9:16 reels/stories | 1080×1920 |

Name files `<YYYY-MM-DD>_<client>_<deliverable>_v<N>.mp4` in `exports/`. After export, list each file with duration, size, loudness and peak.
