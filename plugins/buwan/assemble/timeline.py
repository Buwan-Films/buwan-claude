"""Music-driven timeline plan (Buwan SDE / highlights first cut).

Inputs
  clips      media pool (Clip dicts)              categories  {path: category}  from /buwan:organize
  cull       cull results                         music       music.json (intro + main tracks)
  selects    ordered speech lines (Story-Lock):   [{clip, in, out, beat, part, speaker, text, hold?}]
  sync       sync.json (optional, for multicam angles)
Structure
  Track 1 (intro)  : primary = gap; b-roll cut on bars/beats; title plate marker on the first hit after the soft opening.
  Track 2 (main)   : speech spine in Story-Lock order with gaps; b-roll connected above, cut on beats; cut rate follows
                     the music's energy; burst montage sits on the music's peak; holds (vows, first look) are left clean;
                     outro resolves on the track's tail; logo reveal marker lands before the final beat.
Everything is deterministic: same inputs -> same timeline.
"""
from __future__ import annotations

import bisect
import math
from collections import defaultdict

from common import Clip, log

# b-roll categories (house rules numbering)
SPEECH, PREP, PORTRAITS, CEREMONY, REACT, ESTAB, PARTY, DRONE = (
    "01 Speech", "02 Prep & Details", "03 Portraits", "04 Ceremony", "05 Reactions & BTS", "06 Establishing", "07 Reception & Party", "08 Drone")
BEAT_BROLL = {
    "welcome remarks": [ESTAB, PREP, DRONE], "first looks": [], "about the bride": [PREP, PORTRAITS, REACT],
    "about the groom": [PREP, PORTRAITS, REACT], "power statements": [PORTRAITS, REACT, CEREMONY], "vows": [],
    "kiss": [CEREMONY, REACT], "final wishes": [PARTY, REACT, PORTRAITS], "default": [PORTRAITS, REACT, ESTAB],
}
HOLD_BEATS = {"vows", "first looks"}
MIN_SHOT = 0.55
PART_GAP = 1.5
LINE_GAP = 0.4


def _beats_between(beats, a, b):
    i = bisect.bisect_left(beats, a)
    j = bisect.bisect_left(beats, b)
    return beats[i:j]


def _energy_at(track, t):
    e = track["energy_10hz"]
    i = min(len(e) - 1, max(0, int(t * 10)))
    return e[i] if e else 0.5


def _cut_points(track, t0, t1, mode="energy", t_music0=0.0, targets=(3.0, 2.0, 1.2), bursts=()):
    """Cut times (timeline seconds) between t0 and t1 for a track positioned at t_music0 on the timeline.
    Shot length targets (seconds): low energy, mid energy, peak. Cuts land on beats; long shots land on bars."""
    beats = [b + t_music0 for b in track["beats"]]
    bars = [b + t_music0 for b in track["bars"]]
    peak = [p + t_music0 for p in track["sections"]["peak"]]
    if len(beats) < 2:
        return []
    bi = (beats[-1] - beats[0]) / (len(beats) - 1)
    pts, last = [], t0
    cand = _beats_between(beats, t0, t1)
    for b in cand:
        e = _energy_at(track, b - t_music0)
        in_peak = peak[0] <= b < peak[1]
        target = targets[2] if in_peak else targets[1] if e >= 0.55 else targets[0]
        for (ba, bb, bt) in bursts:          # editor-set burst windows (timeline seconds)
            if ba <= b < bb:
                target = bt
        if mode == "slow":
            target = targets[0] * 1.5
        step = max(1, round(target / bi))
        bar_idx = bisect.bisect_right(bars, b) - 1
        base = bars[bar_idx] if bar_idx >= 0 else beats[0]
        k = round((b - base) / bi)
        if step >= 4 and k % 4 != 0:      # long shots cut on the downbeat
            continue
        if step < 4 and k % step != 0:
            continue
        if b - last < max(MIN_SHOT, target * 0.6):
            continue
        pts.append(b)
        last = b
    return pts


class Pool:
    def __init__(self, clips: dict[str, Clip], categories: dict, cull: dict, sync: dict | None):
        self.clips = clips
        self.cat = categories
        self.cull = cull
        self.used = defaultdict(float)  # seconds used per clip
        self.last_cam = None
        self.sync = (sync or {}).get("clips", {})
        self.realtime = set()   # clips that must never be slowed (speech, multicam angles): Premiere interprets slow-mo project-wide

    def usable(self, path):
        m = self.cull.get(path, {})
        if m.get("reject"):
            return False
        c = self.clips[path]
        if c.kind != "video":
            return False
        if self.cat.get(path) == SPEECH:
            return False
        return True

    def take(self, p, need, src_in=None):
        """A specific clip chosen by the editor (e.g. the final hold)."""
        c = self.clips[p]
        slow = bool(c.fps_num and (c.fps_num / c.fps_den) >= 47) and p not in self.realtime
        factor = ((c.fps_num / c.fps_den) / (24000 / 1001)) if slow else 1.0
        a = src_in if src_in is not None else min(c.duration * 0.25, max(0.0, c.duration - need / factor))
        b = min(c.duration, a + need / factor)
        self.used[p] = max(self.used[p], b * factor + 0.3)
        self.last_cam = c.camera
        return {"clip": p, "in": round(a, 3), "out": round(b, 3), "slowmo": slow}

    def pick(self, categories: list[str], need: float, avoid_warn=("heavy-motion", "dark", "soft-focus"), prefer_slowmo=False):
        cands = []
        for cat in categories or BEAT_BROLL["default"]:
            for p, c in self.clips.items():
                if self.cat.get(p) != cat or not self.usable(p):
                    continue
                m = self.cull.get(p, {})
                warn = set(m.get("warn", []))
                slow = c.fps_num and (c.fps_num / c.fps_den) >= 47 and p not in self.realtime
                avail = c.duration * ((c.fps_num / c.fps_den) / (24000 / 1001) if slow else 1.0) - self.used[p]
                if avail < need + 0.4:
                    continue
                score = 0.0
                score += 3 if cat == (categories or [None])[0] else 0
                score -= 2 if warn & set(avoid_warn) else 0
                score -= self.used[p] / max(1.0, c.duration)  # spread usage
                score += 1 if c.camera != self.last_cam else 0
                score += 1 if (prefer_slowmo and slow) else 0
                cands.append((score, -c.duration, p, bool(slow)))
        if not cands:
            # anything usable
            for p, c in self.clips.items():
                if self.usable(p) and c.duration - self.used[p] >= need + 0.4:
                    cands.append((-5 - self.used[p], -c.duration, p, False))
        if not cands:
            return None
        cands.sort(reverse=True)
        _, _, p, slow = cands[0]
        c = self.clips[p]
        factor = ((c.fps_num / c.fps_den) / (24000 / 1001)) if slow else 1.0
        # source in: skip the first 25% of a fresh clip (handling/settling), then continue from last use
        start_tl = self.used[p] if self.used[p] > 0 else min(c.duration * factor * 0.25, max(0.0, c.duration * factor - need))
        src_in = start_tl / factor
        src_out = min(c.duration, src_in + need / factor)
        self.used[p] = (src_out * factor) + 0.3
        self.last_cam = c.camera
        return {"clip": p, "in": round(src_in, 3), "out": round(src_out, 3), "slowmo": slow}


def build_plan(clips: dict[str, Clip], categories: dict, cull: list[dict], music: dict, selects: list[dict],
               sync: dict | None, name: str, event: str, library: str | None = None, options: dict | None = None) -> dict:
    opt = {"music_bed_db": -20.0, "intro_music_db": -3.0, "burst_music_db": -10.0, "fade_out": 3.0, "logo_lead": 4.5,
           "title_after_s": 12.0, "connected_lane": 1, "hold_min": 15.0,
           # SDE reference (Adrian & Lara): cold open on "before", title closes the film, one long final hold
           "cold_open_s": 12.0, "title_at": "hit", "final_hold_s": 0.0, "face_s": 3.0}
    opt.update(options or {})
    cull_by = {m["path"]: m for m in cull}
    pool = Pool(clips, categories, cull_by, sync)
    pool.realtime = set(opt.get("realtime_clips", [])) | {s["clip"] for s in selects}
    spine, connected, markers_global = [], [], []
    main = music["main"]
    intro = music.get("intro")
    t = 0.0

    # ---------- Track 1: intro ----------
    if intro:
        D1 = intro["duration"]
        spine.append({"gap": True, "at": 0.0, "dur": D1, "markers": [{"t": 0.0, "name": "PART: Intro", "chapter": True}]})
        connected.append({"clip": intro["path"], "in": 0.0, "out": D1, "at": 0.0, "lane": -1, "role": "music", "name": "Music 1 (intro)",
                          "gain_db": opt["intro_music_db"], "fade_in": 0.5, "fade_out": min(2.0, D1 / 4)})
        cuts = [0.0] + _cut_points(intro, 0.0, D1, t_music0=0.0) + [D1]
        order = [ESTAB, DRONE, PREP, PREP, PORTRAITS, ESTAB, PREP, PORTRAITS]
        hits = [h for h in intro["hits"] if h >= opt["title_after_s"]]
        title_t = hits[0] if hits else (intro["bars"][min(len(intro["bars"]) - 1, max(0, len(intro["bars"]) * 3 // 5))] if intro["bars"] else D1 * 0.6)
        if opt["cold_open_s"] > 0:
            # cold open: ~3 s shots of "before" (venue, details), no portraits, then the music's own cut points
            co = opt["cold_open_s"]
            cold = [x * 3.0 for x in range(int(co // 3))] + [co]
            cuts = cold + [c for c in cuts if c > co + MIN_SHOT]
            if cuts[-1] < D1:
                cuts.append(D1)
        for i in range(len(cuts) - 1):
            a, b = cuts[i], cuts[i + 1]
            need = b - a
            if need < MIN_SHOT:
                continue
            if a < opt["cold_open_s"]:
                cats = [ESTAB, PREP, DRONE]
            else:
                cats = [order[i % len(order)]] + [PREP, PORTRAITS, ESTAB]
            pk = pool.pick(cats, need, prefer_slowmo=(_energy_at(intro, a) > 0.6))
            if pk:
                pk.update({"at": a, "lane": opt["connected_lane"], "video_role": "Video.B-roll"})
                connected.append(pk)
        if opt["title_at"] == "hit":
            markers_global.append({"at": title_t, "name": "GRAPHIC: 07.07 SDE title plate (render with /buwan:graphics)", "todo": True})
        t = D1

    # ---------- Track 2: main ----------
    T2 = t
    D2 = main["duration"]
    connected.append({"clip": main["path"], "in": 0.0, "out": D2, "at": T2, "lane": -2 if intro else -1, "role": "music", "name": "Music 2 (story)",
                      "gain_db": opt["music_bed_db"], "fade_in": 0.3, "fade_out": opt["fade_out"]})
    # lay the speech spine with minimal gaps
    items = []
    cur = T2 + PART_GAP
    last_part = None
    for s in selects:
        if last_part is not None and s.get("part") != last_part:
            cur += PART_GAP
        d = s["out"] - s["in"]
        items.append({**s, "at": cur, "dur": d})
        cur += d + LINE_GAP
        last_part = s.get("part")
    spine_end = cur
    # align the climax to the music peak: anchor = kiss, else first power statement in the ceremony, else 70% through
    peak0 = T2 + main["sections"]["peak"][0]
    anchor = next((it for it in items if it.get("beat") == "kiss"), None) or \
             next((it for it in items if it.get("beat") == "power statements" and it.get("part", "").lower().startswith("cer")), None)
    anchor_t = anchor["at"] if anchor else (T2 + 0.7 * (spine_end - T2))
    shift = peak0 - anchor_t
    notes = []
    if shift > 0.5:
        # distribute the shift as breathing room at part boundaries before the anchor
        bounds = [i for i in range(1, len(items)) if items[i].get("part") != items[i - 1].get("part") and items[i]["at"] <= anchor_t]
        if not bounds:
            bounds = [max(0, items.index(anchor) if anchor in items else len(items) // 2)]
        per = shift / len(bounds)
        acc = 0.0
        bi = set(bounds)
        for i, it in enumerate(items):
            if i in bi:
                acc += per
            it["at"] += acc
        spine_end += shift
        notes.append(f"Added {shift:.1f}s of breathing room before the climax so the kiss lands on the music peak at {peak0 - T2:.1f}s into track 2.")
    elif shift < -0.5:
        notes.append(f"WARN: the music peak ({peak0 - T2:.1f}s into track 2) comes {-shift:.1f}s before the climax line. Pick a track with a later peak, or trim earlier lines.")
    film_end = T2 + D2
    if spine_end > film_end - 6:
        notes.append(f"WARN: speech runs {spine_end - (film_end - 6):.1f}s past where the music resolves. Trim selects or use a longer track 2.")
    # primary storyline: gaps + speech
    pos = T2
    parts_seen = set()
    for it in items:
        if it["at"] - pos > 0.01:
            spine.append({"gap": True, "at": pos, "dur": it["at"] - pos})
        mk = []
        if it.get("part") and it["part"] not in parts_seen:
            parts_seen.add(it["part"])
            mk.append({"t": 0.0, "name": f"PART: {it['part']}", "chapter": True})
        mk.append({"t": 0.0, "name": f"{it.get('beat', 'line')}: {it.get('speaker', '')} — {(it.get('text') or '')[:60]}"})
        is_hold = it.get("hold") or it.get("beat") in HOLD_BEATS
        if is_hold:
            mk.append({"t": 0.0, "name": "HOLD — no cutaways"})
        entry = {"clip": it["clip"], "in": it["in"], "out": it["out"], "at": it["at"], "dur": it["dur"], "role": "dialogue",
                 "audio_role": f"dialogue.{it.get('speaker') or 'speech'}", "name": f"{it.get('beat', '')} {it.get('speaker', '')}".strip(), "markers": mk}
        if sync and it.get("mc"):
            entry["mc"] = it["mc"]
        spine.append(entry)
        pos = it["at"] + it["dur"]
    if film_end - pos > 0.01:
        spine.append({"gap": True, "at": pos, "dur": film_end - pos, "markers": [{"t": 0.0, "name": "PART: Outro", "chapter": True}] if not any(i.get("part", "").lower().startswith("out") for i in items) else []})
    # b-roll over the main track: everywhere except holds, and the speaker stays on camera for the opening of each part
    holds = [(it["at"], it["at"] + it["dur"]) for it in items if it.get("hold") or it.get("beat") in HOLD_BEATS]
    if opt["final_hold_s"] > 0 and items:
        holds.append((film_end - opt["final_hold_s"], film_end))
    seen_parts = set()
    for it in items:
        if it.get("part") not in seen_parts:
            seen_parts.add(it.get("part"))
            holds.append((it["at"], it["at"] + min(opt.get("face_s", 3.0), 0.4 * it["dur"])))
    beat_at = {}
    for it in items:
        beat_at[(it["at"], it["at"] + it["dur"])] = it.get("beat", "default")

    def part_for(tt):
        prev = None
        for it in items:
            if it["at"] - PART_GAP - 0.5 > tt:
                break
            prev = it.get("part")
        return prev

    def beat_for(tt):
        for (a, b), bt in beat_at.items():
            if a - 0.5 <= tt < b + LINE_GAP + 0.5:
                return bt
        return "default"

    tg = tuple(opt.get("cut_targets") or (3.0, 2.0, 1.2))
    bursts = [(b["from"], b["to"], b.get("target", 2.2)) for b in opt.get("bursts", [])]
    cuts = [T2] + _cut_points(main, T2, film_end, t_music0=T2, targets=tg, bursts=bursts) + [film_end]
    peak = [T2 + p for p in main["sections"]["peak"]]
    outro0 = T2 + main["sections"]["outro"][0]
    for i in range(len(cuts) - 1):
        a, b = cuts[i], cuts[i + 1]
        if any(h0 - 0.2 <= a < h1 for h0, h1 in holds):
            continue
        # don't cover the first second of a line's first word? keep b-roll (speech-led editing covers lines), but
        # leave the speaker on camera for the first cut of each part: handled by part gaps.
        b = min(b, next((h0 for h0, h1 in holds if h0 > a), b))
        need = b - a
        if need < MIN_SHOT:
            continue
        bt = beat_for(a)
        cats = BEAT_BROLL.get(bt, BEAT_BROLL["default"])
        pt = part_for(a)
        if pt in opt.get("part_broll", {}):
            cats = opt["part_broll"][pt]
        in_peak = peak[0] <= a < peak[1]
        if in_peak:
            cats = opt.get("peak_broll") or [REACT, CEREMONY, PARTY, PORTRAITS]
        for bw in opt.get("bursts", []):
            if bw["from"] <= a < bw["to"] and bw.get("cats"):
                cats = bw["cats"]
                in_peak = True
        if a >= outro0:
            cats = [PARTY, PORTRAITS, DRONE, ESTAB]
        if not cats:
            continue
        pk = pool.pick(cats, need, prefer_slowmo=in_peak)
        if pk:
            pk.update({"at": a, "lane": opt["connected_lane"], "video_role": "Video.B-roll"})
            connected.append(pk)
    if opt["final_hold_s"] > 0 and items:
        hs = max(T2, film_end - opt["final_hold_s"])
        last = items[-1]
        last_end = last["at"] + last["dur"]
        # one single shot (silhouette / night wide) covers the hold wherever the speech clip doesn't
        start = hs if last["at"] >= hs or last_end <= hs else last_end
        if film_end - start > 1.0:
            fh = opt.get("final_hold_clip")
            pk = pool.take(fh["clip"], film_end - start, fh.get("in")) if fh else pool.pick([PORTRAITS, ESTAB, DRONE], film_end - start)
            if pk:
                pk.update({"at": start, "lane": opt["connected_lane"], "video_role": "Video.B-roll", "name": "FINAL HOLD"})
                connected.append(pk)
    markers_global.append({"at": peak[0], "name": "MUSIC PEAK — burst montage", "chapter": False})
    if opt["title_at"] == "end":
        markers_global.append({"at": max(T2, film_end - 10.0), "name": "GRAPHIC: 07.09 wedding title — The Wedding of … (/buwan:title, over the last wide shot)", "todo": True})
        markers_global.append({"at": film_end, "name": "GRAPHIC: 06.08 logo end card — after the title plate, on black (/buwan:end-card)", "todo": True})
    else:
        markers_global.append({"at": max(T2, film_end - opt["logo_lead"]), "name": "GRAPHIC: 06.07 end credits, then 06.08 logo end card (/buwan:end-card)", "todo": True})
    if opt["final_hold_s"] > 0:
        markers_global.append({"at": max(T2, film_end - opt["final_hold_s"]), "name": f"FINAL HOLD — one shot, {opt['final_hold_s']:.0f}s, last vow lines over it", "todo": False})
    # pin global markers to the gap/clip they fall in
    for m in markers_global:
        host = next((s for s in spine if s["at"] <= m["at"] < s["at"] + s["dur"]), spine[-1])
        host.setdefault("markers", []).append({"t": m["at"] - host["at"], "name": m["name"], "todo": m.get("todo", False), "chapter": m.get("chapter", False)})
    plan = {"name": name, "event": event, "library": library, "clips": {p: c.to_json() for p, c in clips.items()},
            "spine": spine, "connected": connected, "include_event_clips": False, "notes": notes,
            "stats": {"intro_s": round(T2, 1), "main_s": round(D2, 1), "total_s": round(film_end, 1), "speech_lines": len(items),
                      "broll_shots": sum(1 for c in connected if c.get("lane", 0) > 0), "spine_end_s": round(spine_end, 1)}}
    return plan


def picture_edl(plan: dict, path: str):
    """CMX3600 of the effective picture (b-roll where present, else primary) for the proof gate."""
    from common import tc, frames, rt_frames, SEQ_FPS
    events = []
    prim = [s for s in plan["spine"] if not s.get("gap")]
    broll = sorted([c for c in plan["connected"] if c.get("lane", 0) > 0], key=lambda c: c["at"])
    # build a piecewise picture track
    total = plan["stats"]["total_s"]
    edges = sorted({0.0, total} | {c["at"] for c in broll} | {c["at"] + (c["out"] - c["in"]) * (2.5 if c.get("slowmo") else 1) for c in broll} | {p["at"] for p in prim} | {p["at"] + p["dur"] for p in prim})
    edges = [e for e in edges if 0 <= e <= total]
    segs = []
    for a, b in zip(edges, edges[1:]):
        if b - a < 1 / 48:
            continue
        mid = (a + b) / 2
        top = next((c for c in broll if c["at"] <= mid < c["at"] + (c["out"] - c["in"]) * (2.5 if c.get("slowmo") else 1)), None)
        src = top or next((p for p in prim if p["at"] <= mid < p["at"] + p["dur"]), None)
        name = plan["clips"][src["clip"]]["name"] if src else "GAP"
        if segs and segs[-1][2] == name and abs(segs[-1][1] - a) < 1e-6:
            segs[-1][1] = b
        else:
            segs.append([a, b, name])
    lines = ["TITLE: " + plan["name"], "FCM: NON-DROP FRAME", ""]
    parts = {s["at"]: m["name"].split(": ", 1)[1] for s in plan["spine"] for m in s.get("markers", []) if m["name"].startswith("PART: ")}
    n = 0
    for a, b, name in segs:
        n += 1
        fa, fb = frames(a), frames(b)
        lines.append(f"{n:03d}  AX       V     C        00:00:00:00 {tc(b - a, base=0)} {tc(a)} {tc(b)}")
        lines.append(f"* FROM CLIP NAME: {name}")
        for pt, pname in parts.items():
            if a <= pt < b:
                lines.append(f"* PART: {pname}")
        lines.append("")
    with open(path, "w") as f:
        f.write("\n".join(lines))
    return path
