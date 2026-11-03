---
name: graphics
description: Pipeline stage 05 — graphics and captions from the Buwan Video Component Kit - plan every beat, render kit components with the job's real names/dates/quotes as ProRes 4444 alpha clips, place them, burn-in or sidecar captions, then QA and converge (3 rounds max). Use for titles, lower thirds, name cards, captions, logo, end card, transitions, or any on-screen text.
argument-hint: "[project folder]"
---

# 05 Graphics + captions

Only kit components. If something isn't in the kit, say so and ask — never improvise a graphic.

## 5a Plan
Storyboard every beat that needs a graphic in `edit/graphics-plan_vN.md`: `record TC · beat · component code · text · duration`. Defaults (house rules): intro → 07.07 SDE title plate or 07.01 couple introduction · vows → 07.02 vow caption · speeches → 07.03 speaker lower third · opening establishing → 07.04 date & venue tag · between parts → dip to black or 03.03 moonrise · end → 06.02 logo reveal + 06.07 end credits. Corporate: 08.xx components, no Italiana.
Check every proper noun against the paper edit's spot-check list. Ask the editor for anything unknown (spellings, roles, venue).

## 5b Build — render with the kit renderer
```
node "${CLAUDE_PLUGIN_ROOT}/scripts/render-kit.js" list                     # all components
node "${CLAUDE_PLUGIN_ROOT}/scripts/render-kit.js" texts 07.03              # its sample text
node "${CLAUDE_PLUGIN_ROOT}/scripts/render-kit.js" render 07.03 --text '{"Paolo Ramirez":"<Name>","Best man":"<Role>"}' --out edit/graphics/07.03_<name>.mov --still
```
- Output: ProRes 4444 + alpha, 23.976, 1920×1080 (social 1080×1920). Works in Premiere, Final Cut and Resolve.
- Map EVERY sample string to real text (or `""` to remove it). The renderer warns about strings it couldn't find.
- View the `--still` PNG of each render before placing it.
- Reusable pieces are pre-rendered in the workspace `kit/` (logo, logo reveal, watermark, letterbox, transition mattes); don't re-render those.
- If the renderer isn't installed: run `/buwan:setup-kit`.

Place them on the top video tracks (Premiere bridge: place directly into a duplicate of the working sequence; Resolve/FCP: list placements with record TC for the editor, or include them in the FCPXML).

### Transitions (same look in every app)
| Kit | How |
|---|---|
| 03.01 Crossfade 1.4s | native Cross Dissolve / Cross Dissolve / Cross Dissolve, 1.4s (34 frames) |
| 03.02 Dip to black | A fades out .7s → black .3s → B fades in .8s (native Dip to Black ≈ 1.8s) |
| 03.03 Moonrise mask | `kit/transitions/03.03_moonrise-matte.mov` as a luma matte for clip B (Premiere: Track Matte Key, Luma; Resolve: matte clip above B, Composite Mode or Fusion MatteControl; FCP: Image Mask effect on B with the matte clip) |
| 03.04 Gold line wipe | `03.04_wipe-matte.mov` as luma matte for B + `03.04_gold-edge.mov` on top |
| 03.05 Light leak | `03.05_light-leak-screen.mov` on top in **Screen** blend mode, over a 1.4s crossfade |
| 03.06 Soft blur | native blur dissolve 1.1s (Premiere: Gaussian Blur keyframes 0→34 on A with dissolve) |
| 03.07 Whip pan | native whip / directional blur 0.45s — SDE energy beats only, never during vows |
| 03.08 Ken Burns | scale 100→122% on A + dissolve, B settles 114→100%, 1.4s |

### Captions
- SRT from `captions/` (verbatim speech). One line, ≤ 8 words, Cormorant 54px on a soft ink wash (kit 07.06 caption styles).
- Long-form master: sidecar SRT (YouTube) unless the client wants burned-in. Reels: burned in.

## 5c Converge (QA gate, 3 rounds max)
Fresh-eyes check of every graphic: spelling and names, on-brand fonts/colors, grain present, safe areas (bottom 180px reserved for lower thirds; social: inside the 1080×1350 safe zone), duration readable (≥ 3s for names), never over a vow line's key word. Defects → rebuild (round 2, 3). After round 3, list remaining issues for the editor instead of looping.

Same-day mode: minimal captions, title plate + end card only, one converge pass.
