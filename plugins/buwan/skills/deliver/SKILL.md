---
name: deliver
description: Stage 09 — hand the finished films to the client and close the job — delivery note and link, revision rounds tracked against the contract, music licence record, backup check, and the archive (what to keep, what to clear, when the cards may be formatted). Use when an editor or the owner says deliver, send to client, client link, revisions, round 2, archive, close the job, backup, "can we format the cards", or after /buwan:export.
argument-hint: "[project folder]"
---

# 09 Deliver and archive

Follow the house rules (`/buwan:house-rules`). Arguments: $ARGUMENTS

The owner/producer sends things to the client; the editor prepares them. Never send anything to a client, upload anywhere, or delete anything yourself — write the files and the checklist, and say who does each step.

## 1. Ready to send (all must be true)
- `/buwan:export` done: every file in `exports/` listed with duration, size, loudness and peak.
- `/buwan:review` signed off (name and date at the top of `edit/review_vN.md`).
- Proper nouns in captions and cards checked by the editor; corporate: names, titles and partner logos checked by the client contact.
- Music licence recorded (step 3).

## 2. Delivery note
Write `exports/DELIVERY.md`:
```
# <film title> — delivery v<N>
Client: …   Shoot: wedding | prenup | corporate   Date of event: …
Files: <name> · <duration> · <resolution> · <size>   (one line per file)
Link: <owner pastes the share link>   Sent by: …   Sent on: …
Revision rounds in the contract: <owner fills>   Used: <n>
```
Draft a short, warm client message (English or Taglish, the owner's choice) that lists what is in the link and how to send notes: one message with timecodes, per film. Corporate: formal register.

## 3. Music licence
For every track in the film, add to `exports/DELIVERY.md`: title, artist, source (Artlist or other), licence or download ID, and the channel the film will be posted on. YouTube claims on a licensed track are cleared with this record. A track without a licence record blocks delivery.

## 4. Revisions
Client notes go through `/buwan:review` step 3 (numbered revision list, house-rule conflicts flagged for the owner). Each round: new export `_v<N+1>`, a new line in `DELIVERY.md` with the round number. When the rounds in the contract are used up, tell the owner before starting another; don't refuse the client yourself.

## 5. Backup check (before anything is cleared)
List, with sizes, where each of these exists, and confirm two copies on two different drives:
- the camera originals (raw folder or `RAW_COPY/`)
- the project: `edit/` (paper edits, storyboard, transcripts, EDL/FCPXML), the app project file, `captions/`
- the masters in `exports/`
Report any item with only one copy as **NOT SAFE** and stop there.

## 6. Archive and close
Only after the client's final approval and a clean backup check:
- Keep: camera originals, `edit/`, the app project, `captions/`, `exports/` masters, `DELIVERY.md`.
- Can be cleared (the editor decides, Claude never deletes): `_ENHANCED_` and `_SPEECH_` folders (they can be re-made from the originals with `/buwan:basics` and `/buwan:multicam`), render caches, proxies, preview files.
- The cards may be formatted only when the backup check passed and the owner says so. Say this in one line.
- Write `edit/CLOSED.md`: final version, approval date, where the two copies live, what was cleared.
