---
name: title
description: Put the couple's names on the film the Buwan way (kit 07.09 "Wedding title") — over the last calm wide shot of the couple, no panel: "The Wedding of" in Cormorant at the top, the names in wide-tracked Cinzel capitals across the middle ("M A R Y  N H O R   A N D   J O M A R"), a gold hairline, "Buwan Films" small in gold at the foot; it fades in out of a soft blur, holds, and fades out by itself before the 06.08 logo end card. Rendered with the couple's real names as a ProRes 4444 alpha clip, placed in Premiere through the bridge or in Final Cut / Resolve by hand. Use when an editor says "names of the couple", "couple title", "The Wedding of", "title at the end", "add their names", or finishes an SDE / highlight film.
argument-hint: "\"<Name> and <Name>\" [sequence name]"
---

# Wedding title (07.09)

Load `/buwan:house-rules`. The title is a kit graphic: same fonts, sizes, colors and motion on every film. Never restyle it, never use another studio's wording. Arguments: $ARGUMENTS

**The look** (kit 07.09, 1920×1080, 23.976, 7.4 s, transparent):
- 0.2 s "The Wedding of" — Cormorant Garamond 50 px, ivory, top centre, out of a soft blur
- 0.7 s the names — Cinzel 52 px capitals, ivory, tracking opening from .62 em to .92 em across the middle of the frame
- 1.6 s a short gold hairline under the names · 1.9 s "BUWAN FILMS" Cinzel 20 px gold at the foot
- holds · everything fades out 6.2–7.2 s · soft shadow only, no panel, no letterbox

## 1. The names
- Ask once if not given. Write them as the couple are known on the day, in the order the studio uses for the film (bride first unless the editor says otherwise), joined by **"and"** — e.g. `Mary Nhor and Jomar`. Check the spelling against the project name, the invitation or the editor; flag anything unsure before rendering (house rule: proper nouns are checked before they ship).
- Up to **20 characters** in all fit the frame at full tracking. Longer: use first names or nicknames — ask the editor which.

## 2. Render
```
node "${CLAUDE_PLUGIN_ROOT}/scripts/render-kit.js" render 07.09 --text '{"Tina and Vern":"<Name> and <Name>"}' --out "<project>/edit/graphics/07.09_wedding-title.mov" --still
```
Show the still (`07.09_wedding-title.png`) to the editor. A warning "text not found" means the kit changed — run `render-kit.js texts 07.09`.

## 3. Place
Over the **last calm wide shot of the couple**, before the 06.08 logo end card. It needs about 7 s of picture under it; the picture dips to black as the title fades.
- **Premiere (bridge):** `node "${CLAUDE_PLUGIN_ROOT}/../buwan-premiere/scripts/premiere-snippet.js" title - "{file:'<project>/edit/graphics/07.09_wedding-title.mov', sequence:'<their sequence>'}"` → run the printed code with `execute_extendscript`. It imports the title once into `11 Graphics` and lays it on the first free track above V1 over the last 7.4 s of picture (or `{at:<sec>}`), with a marker. Nothing in the cut moves.
- **Final Cut:** import (Leave files in place) → playhead ~7.4 s before the end of the last shot → **Connect** (Q) above it.
- **Resolve:** Media Pool → import → drop on V2 over the last shot.
- Then the end card: `/buwan:end-card`.

## Check
Play the last 20 s: the names sit on a calm wide shot (not a cut mid-title, not a busy or very bright area behind the names); the title is gone before the dip to black; the 06.08 logo end card follows. Report: the names as rendered, sequence, timecode, track.
