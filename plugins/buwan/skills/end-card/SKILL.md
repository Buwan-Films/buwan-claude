---
name: end-card
description: Close a Buwan film with the logo end card (kit 06.08) — two crescent blades sweep in from opposite sides and draw two interlocking rings that glide together into the logo ring ("two become one"); on a warm bloom and a heartbeat the official emblem snaps in from shards, a ring of crescent moons bursts out and more drift and turn, a soft gold glow and a sheen, BUWAN / FILMS rise out of a blur, a slow push-in, then it fades to black (7.7 s). Placed after the last picture of the editor's cut (after the 07.09 wedding title), in Premiere through the bridge, in Final Cut or Resolve by hand, or appended to an already-exported film. Use when an editor says "end card", "logo at the end", "outro logo", "close with the logo", "add our logo like the reference", or finishes an SDE / highlight film.
argument-hint: "[sequence name | exported film path]"
---

# Logo end card (06.08)

Load `/buwan:house-rules`. The card is a kit graphic: never redraw or restyle the logo, never invent another outro. Arguments: $ARGUMENTS

**The card:** `kit/wedding/06.08_logo-end-card.mov` in the workspace (ProRes 4444, 1920×1080, 23.976, 7.7 s, opaque on near-black, no audio; still: `06.08_logo-end-card.png`). Made by `/buwan:setup-kit` (kit prerender); if it's missing, `node "${CLAUDE_PLUGIN_ROOT}/scripts/render-kit.js" render 06.08 --out kit/wedding/06.08_logo-end-card.mov --still`.
- 0.2–0.75 s — two crescent blades, one from each side, sweep in and cross over the logo; small Buwan crescents break off along each cut
- 0.8–1.85 s — they draw two interlocking rings (wedding bands) that glide together into the logo's ring
- 1.85 s — a warm ivory bloom and a heartbeat pulse; the official emblem (the logo file itself, cut into shards) snaps in; a soft gold glow rises behind it
- 1.85 s a ring of 18 crescent moons bursts out from the logo and turns away · crescent moons of every size (gold, ivory) drift and turn throughout · 2.8 s BUWAN, 3.3 s FILMS rise out of a blur; a light sheen crosses the gold
- slow push-in the whole time · fades to black 6.4–7.3 s · 0.4 s of black after

**Where it goes:** the very last shot. On an SDE / highlight film the order is: final wide shot with the **07.09 wedding title** ("The Wedding of …", `/buwan:title`) dipping to black → **06.08 logo end card**. With end credits: 06.07 credits → 06.08. Nothing after it. The music rings out under the card and is faded out by its end (about −20 dB under the logo is right; never a hard cut at the picture's last frame).

## Apply
Ask once which sequence (Premiere) or project (Final Cut / Resolve) is the film, if it isn't clear. Only ever **append** after the last picture — nothing already in the editor's cut moves.

- **Premiere (bridge):** `node "${CLAUDE_PLUGIN_ROOT}/../buwan-premiere/scripts/premiere-snippet.js" endcard - "{file:'<workspace>/kit/wedding/06.08_logo-end-card.mov', sequence:'<their sequence>'}"` → run the printed code with `execute_extendscript`. It imports the card once into `11 Graphics`, lays it on V1 right after the last video clip (or `{at:<sec>}`), and adds a marker. Then tell the editor to extend the music tail ~7.7 s past the picture and fade it out by the card's end.
- **Final Cut:** import `06.08_logo-end-card.mov` (Leave files in place) → put the playhead at the end of the last clip → **Append** (E). Extend the music's tail and fade it (Option-drag the fade handle) to the card's end.
- **Resolve:** Media Pool → import the .mov → playhead at the end → **Edit → Append to End of Timeline** (Shift+F12). Extend the music and fade it out in Fairlight.
- **Already exported film (any app):** `node "${CLAUDE_PLUGIN_ROOT}/scripts/end-card.js" append "<film.mp4>" [--fade-tail 2]` → `<film>_endcard.mp4` next to it (the film is never overwritten): the card conformed to the film's size and frame rate, the film's sound kept and padded with silence under the card. Use `--fade-tail` when the film's music ends abruptly.

## Check
Play the last 15 s: title plate → black → the logo folds in, no flash frame or gap between them, the music fading under the logo and silent by the end. Report: where it was placed (sequence, timecode, track) and the music tail to fix by hand, if any.
