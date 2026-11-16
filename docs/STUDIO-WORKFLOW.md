# Buwan Films studio workflow

Plan → Shoot → Edit → Deliver, for wedding, prenup, corporate and commercial / reels shoots. The visual version is the [Studio flow](https://claude.ai/artifact/XspJWQPLCpuhofjkyzse7d) page (a copy is in `plugins/buwan/reference/studio-flow.html`). Who does each step: [ROLES.md](ROLES.md).

## 1. Plan (weeks before) — Storyboard page
1. **Brief:** client, shoot type, films promised, date, venue, team, deadlines.
2. **Music:** wedding two tracks (intro, then story to the end, with the switch beat); prenup one track; corporate a brand-safe bed.
3. **Beats:** start from the template for the shoot type. Wedding: the 8 audio layers in the SDE shape. Prenup: the shot flow. Corporate: welcome → keynote → exec quotes → panel → crowd → awards → partners → CTA. Commercial: hook → problem → product hero → details → people using it → testimonial → offer → CTA → logo, from the client-approved script (Script-Lock). Speech beats stay empty until Story-Lock.
4. **Shot list:** made from the beats, per camera (Creative / Glider, Main, 3rd Cam, Drone, Audio), must-haves first.
5. **Cards:** couple title, date and venue, save-the-date, lower thirds. Their text is known now, so they can be rendered before the day.
6. **Client sign-off** on beats, music, names and spellings. *Gate.*
7. **Export the bundle** → the job's `edit/storyboard/`.

## 2. Shoot
| | Wedding | Prenup | Corporate | Commercial / reels |
|---|---|---|---|---|
| Shape of the day | prep → ceremony → reception, live | look by look, location by location | the run of show | scene by scene from the script |
| Shot list | ticked live, clip names noted | ticked per look | ticked per session, every sponsor logo | hook and product hero first, a text-safe plate per super |
| Footage | `/buwan:basics`, then `/buwan:sync` per new card (transcripts on arrival) | `/buwan:basics` after the shoot, all cards at once | `/buwan:basics` + `/buwan:sync`, brand-true white balance | `/buwan:basics`, brand-true white balance |
| Speech | `/buwan:multicam` for vows, letters, speeches | voice-over only if planned | `/buwan:multicam` for keynotes and panels | `/buwan:multicam` for testimonials and voice-over |
| Coverage | must-haves still missing go back to the lead shooter during the day | missing shots → pickup | missing logos and speakers flagged during the event | missing shots before talent and product leave |

Every card: two copies on two drives before anything else. Cards are never formatted until delivery is closed.

## 3. Edit
1. Import into the app (`assemble.js premiere-import`).
2. **Story-Lock** `/buwan:plot`, from the storyboard skeleton and the real transcripts. Prenup: **Shot-Lock** (best take per planned shot). Commercial: the best take of every scripted line, testimonials verbatim. *Gate: editor approves.*
3. **Rough cut** `/buwan:rough-cut`: b-roll by shot from the shot list, hold/burst as planned, music peaks.
4. **Proof gate** `/buwan:proof-gate` (wedding, prenup, corporate, SDE targets). *Gate.*
5. Audio `/buwan:audio` and graphics placement `/buwan:graphics` (can run side by side; neither changes the cut), then grade `/buwan:grade`, then SFX `/buwan:sfx`.
6. **Review** `/buwan:review`, against the storyboard and the client notes. *Gate: owner signs off.*

## 4. Deliver
1. **Export** `/buwan:export`: wedding master and reels; prenup film, save-the-date and teasers; corporate 16:9 recap, 1:1 LinkedIn and reels; commercial spots 60 / 30 / 15 / 6 s, 9:16 reels, 1:1 / 4:5 feed and clean versions.
2. **Deliver** `/buwan:deliver`: `exports/DELIVERY.md` (files, link, client message), music licence record, revision rounds against the contract.
3. **Backup check:** originals, project and masters on two drives. *Gate.*
4. **Archive and close:** `edit/CLOSED.md`; the owner says when the cards may be formatted.

## Faster without losing quality
- Do in Plan everything that doesn't need the footage: cards rendered, look picked, timeline skeleton (music + beat markers + cards) ready before the day.
- The shot list's clip names let the rough cut find b-roll without searching through bins.
- Transcripts are made as the cards arrive, so Story-Lock starts from text.
- Audio and graphics placement run side by side after the proof gate.

## Shoot type in the engine
Name the project `<date>_<client>_<type>` with type `wedding`, `prenup`, `corporate` or `commercial` (`_reels` counts as commercial), or pass `--shoot <type>` once. The basics then pick the white balance policy (weddings and prenups keep natural warmth; corporate and commercial are brand-true), `/buwan:sync` labels the transcripts for that shoot (vows · mass · toasts / keynote · panel · awards / testimonial · script), and the proof gate measures the right pacing.

## Open items
- **Coverage check:** today it uses the clip names the shooters type. Matching clips to shots without that note is not built.
- **Call sheet:** the times and places of the day are written in the storyboard brief for now.
- **CRM:** clients, bookings, contracts and payments come next, once this flow is settled.
