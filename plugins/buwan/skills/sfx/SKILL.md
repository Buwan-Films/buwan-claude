---
name: sfx
description: Pipeline stage 06 — sound design from the placed graphics and transitions (whooshes, risers, hits, ambience) and the optional music bed at a flat −20 dB, under the dialogue. Use when an editor says SFX, sound design, whoosh, riser, ambience, or after graphics are placed.
argument-hint: "[project folder]"
---

# 06 SFX

SFX follow the placed graphics (Edit Pipeline: "SFX from placed graphics"). Music bed is **opt-in**, flat **−20 dB**.

1. Read the graphics plan and the timeline's transitions. For each:
   - title / logo reveal → soft riser into it, low hit on the reveal
   - lower third / tag → subtle swish (−28 to −24 dB)
   - whip pan → whoosh synced to the cut
   - moonrise / light leak → shimmer or swell
   - dip to black → let it breathe; no SFX unless the editor asks
2. Ambience: room tone or venue ambience under dialogue gaps so cuts don't drop to silence.
3. Sources: the studio's licensed SFX library in `kit/sfx/` (if present) — never download unlicensed sounds. If the library is missing, list the SFX needed with timecodes for the editor.
4. Levels: SFX never louder than dialogue; check the mix still meets −17 LUFS / −6 dBFS peak (re-run the measurement from `/buwan:audio`).
5. Place on dedicated SFX tracks (color: SFX & Ambience). Report a cue list: `TC · cue · file · level`.
