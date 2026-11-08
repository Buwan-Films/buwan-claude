---
name: multicam
description: Multicam sync on request — merge the cameras that covered the same moment (vows, interviews, speeches, the ceremony) into synced multicam clips, matched by audio so wrong camera clocks don't matter. Not part of the basics; the editor asks for it. Use when an editor says "sync", "multicam", "merge the cameras", "sync the vows / interview / ceremony", or names cameras to align.
argument-hint: "<project> [--anchor <camera that rolled longest>] [--trusted <cameras with correct clocks>]"
---

# Multicam sync (on request)

Load `/buwan:house-rules` and the app playbook. The basics (`/buwan:basics`) must have run (`clips.json`, `cull.json`, `categories.json` exist). Arguments: $ARGUMENTS

1. Ask once, if not given: which camera rolled longest on the moment (the **anchor**), and which cameras have a correct clock (**trusted**). Default anchor = the main camera.
2. `node "${CLAUDE_PLUGIN_ROOT}/scripts/assemble.js" sync <project> --anchor "<camera>" --trusted <cameras…>` → `sync.json` + `multicams.json`. It matches sound (cross-correlation), so a camera whose clock was never set still lands to the frame. Report: clips synced by audio · by timestamp · unsynced, and the multicam groups found (name, cameras, duration). If the editor only wants one moment (the vows, one interview), keep only those groups when you apply — name them by what they cover.
3. Apply:
   - **Premiere:** `assemble.js premiere <project>` (re-writes the manifest with the groups) → bridge `sync` → one **SYNC <group>** sequence per group, each camera on its own track at its audio offset. Editor: Project panel → right-click the SYNC sequence → **Multi-Camera → Enable**, then cut angles with the 1–9 keys in the Multi-Camera monitor.
   - **Final Cut:** `assemble.js organize <project> --multicam --event "<Couple>"` → the organize FCPXML now carries the synced multicam clips. Import; the angles are aligned.
   - **Resolve:** import the same FCPXML (File → Import → Timeline), or Create Multicam Clip Using Selected Clips → Sync by Audio inside Resolve.
4. Report groups and what the editor enables by hand. The A-Roll clean, the labels and the bins are untouched.
