---
name: bts
description: Behind-the-scenes for social media on every shoot (wedding, prenup, corporate, commercial / reels) — plan the BTS shots from the storyboard, keep the BTS clips as shot in the 5-BTS camera folder, pick the best ones, draft 9:16 posts with captions and hashtags for Facebook, Instagram and TikTok (and YouTube Shorts), and check the posting rules (earliest post date, client OK, music, tags) before anything goes up. Use when anyone says BTS, behind the scenes, social post, story, TikTok, IG reel, FB post, "what can we post", or after a shoot day.
argument-hint: "[project folder] [plan | pick | post]"
---

# BTS — behind the scenes for social

Load `/buwan:house-rules`. There is a BTS shooter on every shoot. BTS is for the studio's social pages, not for the film: it is never cut into the film unless the editor decides to, and nothing is posted before the earliest post date. Claude Code drafts; **a person posts**. Never upload or post anything yourself.

## 1. Plan (before the shoot)
Read `edit/storyboard/storyboard.json` if it exists: the beats with `cam: "BTS"` (or `social: true`) are the BTS shot list, and `social` holds the platforms, the earliest post date, the client's OK, the tags and the posting plan. If there is no storyboard, ask for those five things once and write `edit/social/bts-plan.md`.

What the BTS shooter gets, per shoot type (add the storyboard's own BTS shots):
| Shoot | Shoot this | Never post |
|---|---|---|
| Wedding | crew at work (glider move, drone launch, the SDE being cut at the reception), guests' reactions shot from behind the crew, the venue being set up | the bride's look before the ceremony; the SDE before it is screened; anything the couple asked to keep private |
| Prenup | directing the prompts, the golden-hour setup, laughs between takes | the couple's faces before they OK it |
| Corporate | setup before doors open, the run of show from behind the cameras, the sizzle being cut | confidential slides, screens, unreleased products, attendees who asked not to be filmed |
| Commercial / reels | set and lighting build, the product hero setup, the talent between takes | anything before the client's launch date; the product or the talent without the client's OK (check the NDA) |

Shooting: vertical 9:16 on the phone or the BTS camera, steady, 3–10 s per clip, sound on. Cards or phone exports go into the raw folder's **`5-BTS`** camera folder.

## 2. On the day
- The basics and `/buwan:sync` copy `5-BTS` into the `_ENHANCED_` folder exactly as shot: no exposure or white balance fix (phone HDR stays as it is), no cull, no transcript. In Premiere they land in their own `5-BTS` bin, label **Rose**, Description "BTS for social".
- A same-day story is allowed only if the plan says so and the earliest post date has passed (wedding: usually after the SDE screening).

## 3. Pick
List the `5-BTS` clips: name, length, vertical or not, and what they show (look at one frame per clip). Mark the best 8–15 for a BTS reel and 3–5 for stories. Leave out clips that break the "Never post" column. Write `edit/social/bts-picks.md`.

## 4. Draft the posts
For each planned post write `edit/social/posts.md`: platform · post type (story / reel / feed) · clips in order with in/out · length · caption · hashtags · tags · music · earliest post date.
- **Specs:** 9:16 1080×1920, hook in the first 2 s, text and the logo kept out of the top ~250 px and the bottom ~350 px (platform UI), captions on (most people watch muted). Reels and TikTok 15–60 s; stories ≤ 15 s per card. Facebook: the same 9:16 file as the reel.
- **Brand:** kit **05 Social** components only (05.04 BTS label, 05.03 location tag, 05.01 hook screen, 05.08 CTA end screen); render them with `/buwan:graphics` like any kit clip.
- **Captions:** short, warm, English or Taglish to match the studio's voice; name the couple or client only if the plan has their OK. Tags from the plan (always @buwanfilmsph, plus the couple's or client's handle and the suppliers if the plan lists them).
- **Music:** the platform's own licensed sounds, or a track whose licence covers social. Never the film's track before the film is delivered.
- The BTS person cuts the post (phone app or Premiere); if the editor wants, Claude can assemble a rough 9:16 from the picks with ffmpeg and the kit label, for them to finish.

## 5. Before anything is posted (all must be true)
- The earliest post date has passed and the client's OK is "yes" (or the owner says so in writing).
- Nothing in the post breaks the "Never post" column.
- Names and handles spelled right.
- Music cleared as above.
Then the BTS person or the owner posts and adds the link and date to `edit/social/posts.md`.
