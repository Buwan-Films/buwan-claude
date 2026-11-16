# Who does what at Buwan Films

One page per role: what you do before, on and after the shoot, which page or skill you use, and when your part is done. The full picture is the [Studio flow](https://claude.ai/artifact/XspJWQPLCpuhofjkyzse7d) (switch wedding / prenup / corporate at the top). The order of the steps is in [STUDIO-WORKFLOW.md](STUDIO-WORKFLOW.md).

One person can hold more than one role. On a small wedding the lead shooter is often also on audio, and the on-site editor is also the data wrangler.

---

## Owner / producer
**You own the client and the plan.**

| When | What you do | Where |
|---|---|---|
| Booking | Brief: shoot type, films promised, date, venue, team, deadlines, revision rounds in the contract | Storyboard page → Brief and team |
| Weeks before | Build the storyboard with the editor: beats, music, cards, shot list. Get the client's sign-off on beats, music, names and spellings | [Storyboard](https://claude.ai/artifact/LJpY3x7t19hgkKZuE1Ed9D) |
| Weeks before | Licence the music (Artlist) and keep the licence ID | Storyboard → Music |
| Before the day | Export the storyboard bundle (.zip) and send it to the editor; share the Shot list view with the shooters | Storyboard → Export |
| After the edit | Taste review with the editor; decide on client requests that break house rules | `/buwan:review` |
| Delivery | Send the link and the message the editor drafted; track revision rounds; say when the cards may be formatted | `/buwan:deliver` → `exports/DELIVERY.md` |

**Done when:** the client approved the final version and `edit/CLOSED.md` says where the two backup copies live.

---

## Lead shooter (director on the day)
**You make sure the plan gets shot.**

- Before: read the storyboard in Board view, then the Shot list. Assign every camera (Creative / Glider, Main, 3rd Cam, Drone, Audio) to a person. Ask the owner about anything unclear while there is still time.
- Camera setup for everyone: S-Cinetone 10-bit on A7 IV-class bodies, never S-Log on same-day jobs, white balance in Kelvin (never auto), the agreed frame rate per role. Drone: Normal color on SDE days.
- On the day: keep the Shot list open on your phone. Must-haves first. If a must-have can't be shot (rain, timing), tell the editor and the owner right away so the story can change.
- Card handoff: every card goes to the data wrangler labeled with its camera folder name. Never format a card on the day.

**Done when:** every must-have is ticked, or the missing ones are reported.

---

## Shooters (Creative / Glider, Main, 3rd Cam, Drone)
**You get your camera's shots on the list.**

- Before: open the Shot list, filter to your camera. Know your must-haves.
- On the day: tick each shot as you get it and type the clip name if you can (e.g. `C0823`). That one tap saves the editor minutes of searching later.
- Creative / Glider: the basics smooth shaky glider shots, but a steady 5-second take is always better than a long wobbly one.
- Hand every card to the data wrangler, labeled. Don't delete clips in camera.

**Done when:** your list is ticked and your cards are handed over.

---

## Audio (lav and recorder)
**Speech is the spine of every wedding and corporate film. If the audio is bad, the story is gone.**

- Before: from the storyboard, list every speech moment (letters, vows, speeches, keynotes) and plan who wears a lav and where the recorder sits.
- On the day: lav on the groom (or the speaker), recorder at the podium or officiant, levels checked. Clap or a clear sound at the start of each moment helps the sync.
- Audio files go in the `Audio` folder of the cards.

**Done when:** every planned speech moment has at least one clean recording.

---

## Data wrangler / on-site editor
**You keep the footage safe and moving.**

- Copy every card to the SSD into its camera folder (`1-Creative/Glider`, `2-Main`, `3-3rd Cam`, `4-Drone`, `Audio`), then make a second copy on a different drive. Keep the cards until the owner says they may be formatted.
- First cards: `/buwan:basics` (Premiere: `/buwan-premiere:wedding-day`). Later cards: `/buwan:sync` (new clips only, transcripts made on this computer).
- Tell the lead shooter which must-haves are still missing.

**Done when:** every card has two copies and is in the `_ENHANCED_` folder.

---

## Editor
**You turn the plan and the day into the film.** Your Claude Code does the heavy lifting; you make the calls.

| Step | Skill | Your call |
|---|---|---|
| Set up | Premiere project, music placed, unzip the storyboard bundle into `edit/storyboard/` | — |
| Import | `assemble.js premiere-import <project>` | — |
| Speech moments | `/buwan:multicam` (on request) | which clips belong to one moment |
| Story-Lock | `/buwan:plot` | approve the paper edit. Prenup: approve the Shot-Lock |
| Rough cut | `/buwan:rough-cut` | the b-roll that serves each line |
| Proof gate | `/buwan:proof-gate` | fix or write an override reason |
| Audio · grade · graphics · SFX | `/buwan:audio`, `/buwan:grade`, `/buwan:graphics`, `/buwan:title`, `/buwan:end-card`, `/buwan:sfx` | the look, name spellings |
| Review | `/buwan:review` with the owner | taste |
| Export | `/buwan:export`, `/buwan:clipper` | — |
| Deliver | `/buwan:deliver` prepares the note, the music licence record and the backup check | — |

Same-day edit: `/buwan:sde` runs Story-Lock to export compressed for the reception. The gates still apply.

**Done when:** the files are exported, `DELIVERY.md` is ready for the owner, and the backup check says SAFE.

---

## Studio rules everyone follows
- Raw footage is never touched. Claude Code only reads the raw folders.
- The storyboard is a plan. What people actually said on the day goes on screen, word for word, Taglish kept.
- The gates (client sign-off, Story-Lock, proof gate, review) apply in same-day mode too.
- Graphics come only from the Buwan Video Component Kit.
- Spell-check every name before captions ship.
