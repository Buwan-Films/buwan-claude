---
name: organize
description: Organize a Buwan project's clips — log every clip into the studio categories, build the standard bins, and color the clips (Premiere labels, Resolve clip colors, Final Cut roles) with the shared Buwan color scheme. Use after intake, or when an editor says organize, sort, label, color clips, bins, or "clean up the project".
argument-hint: "[project folder]"
---

# Organize clips (after 01 Intake)

The categories, bin names and colors are in `/buwan:house-rules` → "Clip categories, bins and colors". Use exactly those — never invent a category or color.

## 1. Build the clip log
For every clip in `sources/footage` and `sources/audio` (read-only — read, never write):
1. `ffprobe` it: duration, resolution, fps, audio channels, creation time.
2. Measure audio: `ffmpeg -i <clip> -af "silencedetect=n=-35dB:d=2,ebur128" -f null -` — long non-silent stretches with speech-level loudness suggest **01 Speech**.
3. Look at it: extract 3 thumbnails (10%, 50%, 90%) with `ffmpeg -ss <t> -i <clip> -frames:v 1 -vf scale=480:-2 edit/thumbs/<clip>_<n>.jpg` and **view them**. Decide the category from what you actually see (rings on a table = Details; empty ballroom = Establishing; crying guest = Reactions; aerial = Drone).
4. Use the folder segment (prep / ceremony / reception) and timestamps as tie-breakers.
5. If unsure, pick the closest category and mark `confidence=low`.

Write `edit/clip-log.csv`:
```
clip,path,segment,category,color_premiere,color_resolve,role_fcp,duration,has_speech,speaker,confidence,notes
```
Show the editor a summary (count per category) and the low-confidence clips. Let them correct before applying.

## 2. Apply in the editor's app
Follow the editor's playbook (`${user_config.nle}`):

**Premiere Pro (bridge):** create bins `01 Speech` … `12 Grade & Adjust`, `Sequences`; move each project item into its bin; set its label color. Clips already in sequences take the item's label. Save the project. If the bridge isn't connected, generate `edit/organize-premiere.md` with the steps instead.

**DaVinci Resolve:** Studio with scripting enabled → create the bins and call `SetClipColor` on each MediaPoolItem (and TimelineItem if a timeline exists). Free version → write `edit/organize-resolve.md`: one section per bin with the clip list; the editor selects them and uses **right-click → Clip Color**.

**Final Cut Pro:** write `edit/organize_vN.fcpxml` with an `<event>` containing every clip as an `<asset-clip>` with `videoRole`/`audioRole` set from the table (e.g. `videoRole="Video.Reactions"`, `audioRole="dialogue.Paolo Ramirez"`) and a `<keyword>` per category, plus keyword collections named like the bins. Tell the editor once: **Modify → Edit Roles** → set the role colors from the table (FCP remembers them per library).

## 3. Report
Table: category · clips · total duration · color. Then the low-confidence list and anything that couldn't be classified.
