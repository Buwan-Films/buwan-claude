"""Deterministic FCPXML 1.11 writer for Final Cut Pro (also imports into DaVinci Resolve).

Takes a plan dict (see timeline.py / assemble.py) and writes one .fcpxml with:
  resources   one <format> per distinct frame size/rate, one <asset> per media file (probed, never guessed),
              <media><multicam> for synced angles
  event       every clip with keywords (bins), roles, ratings (rejected), notes
  project     the timeline: primary storyline (speech + gaps), connected b-roll (lane 1+), music (lane -1/-2),
              markers, slow-motion conform, volume adjustments, fades
All times are rational and on the frame grid. Sequence is 23.976 NDF starting 01:00:00:00.
"""
from __future__ import annotations

from fractions import Fraction
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

from common import Clip, SEQ_FPS, SEQ_START_TC, rt, rt_frames, rt_samples, frames, file_url, slug

FORMAT_NAMES = {
    (1920, 1080, "23.98"): "FFVideoFormat1080p2398", (1920, 1080, "24"): "FFVideoFormat1080p24", (1920, 1080, "25"): "FFVideoFormat1080p25",
    (1920, 1080, "29.97"): "FFVideoFormat1080p2997", (1920, 1080, "30"): "FFVideoFormat1080p30", (1920, 1080, "50"): "FFVideoFormat1080p50",
    (1920, 1080, "59.94"): "FFVideoFormat1080p5994", (1920, 1080, "60"): "FFVideoFormat1080p60",
    (3840, 2160, "23.98"): "FFVideoFormat3840x2160p2398", (3840, 2160, "24"): "FFVideoFormat3840x2160p24", (3840, 2160, "25"): "FFVideoFormat3840x2160p25",
    (3840, 2160, "29.97"): "FFVideoFormat3840x2160p2997", (3840, 2160, "30"): "FFVideoFormat3840x2160p30", (3840, 2160, "50"): "FFVideoFormat3840x2160p50",
    (3840, 2160, "59.94"): "FFVideoFormat3840x2160p5994", (3840, 2160, "60"): "FFVideoFormat3840x2160p60",
    (1080, 1920, "23.98"): "FFVideoFormat1080x1920p2398", (1080, 1920, "29.97"): "FFVideoFormat1080x1920p2997", (1080, 1920, "30"): "FFVideoFormat1080x1920p30",
}
CONFORM_OK = {"23.98", "24", "25", "29.97", "30", "48", "50", "59.94", "60"}
ROLE_COLORS_NOTE = "Set role colors once: Modify > Edit Roles (see Buwan house rules)."


class Writer:
    def __init__(self, plan: dict):
        self.plan = plan
        self.clips: dict[str, Clip] = {p: (c if isinstance(c, Clip) else Clip.from_json(c)) for p, c in plan["clips"].items()}
        self.res: list[str] = []
        self.fmt_ids: dict[tuple, str] = {}
        self.asset_ids: dict[str, str] = {}
        self.mc_ids: dict[str, str] = {}
        self.mc_meta: dict[str, dict] = {}
        self.n = 0
        self.seq_fmt = self._format(plan.get("width", 1920), plan.get("height", 1080), "23.98")

    # ---------- resources ----------
    def _rid(self):
        self.n += 1
        return f"r{self.n}"

    def _format(self, w, h, label):
        key = (w, h, label)
        if key in self.fmt_ids:
            return self.fmt_ids[key]
        rid = self._rid()
        fd = {"23.98": "1001/24000s", "24": "100/2400s", "25": "100/2500s", "29.97": "1001/30000s", "30": "100/3000s", "48": "100/4800s",
              "50": "100/5000s", "59.94": "1001/60000s", "60": "100/6000s", "119.88": "1001/120000s", "120": "100/12000s"}.get(label, "1001/24000s")
        name = FORMAT_NAMES.get(key, f"FFVideoFormat{w}x{h}p{label.replace('.', '')}")
        self.res.append(f'<format id="{rid}" name="{name}" frameDuration="{fd}" width="{w}" height="{h}" colorSpace="1-1-1 (Rec. 709)"/>')
        self.fmt_ids[key] = rid
        return rid

    def asset(self, path: str) -> str:
        if path in self.asset_ids:
            return self.asset_ids[path]
        c = self.clips[path]
        rid = self._rid()
        attrs = [f'id="{rid}"', f"name={quoteattr(c.name)}", f'uid="{slug(c.rel or c.name)}-{abs(hash(path)) % 10**8}"', 'start="0s"']
        if c.kind == "video" and c.fps_num:
            fps = Fraction(c.fps_num, c.fps_den)
            attrs.append(f'duration="{rt(c.duration, fps)}"')
            attrs.append(f'format="{self._format(c.width, c.height, c.fps_label)}"')
            attrs.append('hasVideo="1"')
        else:
            attrs.append(f'duration="{rt_samples(c.duration, c.audio_rate)}"')
        if c.has_audio:
            attrs += ['hasAudio="1"', 'audioSources="1"', f'audioChannels="{c.audio_channels}"', f'audioRate="{c.audio_rate}"']
        self.res.append(f'<asset {" ".join(attrs)}><media-rep kind="original-media" src={quoteattr(file_url(path))}/></asset>')
        self.asset_ids[path] = rid
        return rid

    def multicam(self, mc: dict) -> str:
        """mc = {id, name, angles:[{name, clips:[{clip, offset}]}]}; offsets in seconds on the multicam's own timeline."""
        if mc["id"] in self.mc_ids:
            return self.mc_ids[mc["id"]]
        rid = self._rid()
        angles = []
        for i, a in enumerate(mc["angles"]):
            aid = f"{mc['id']}a{i+1}"
            inner, pos = "", 0.0
            for cl in sorted(a["clips"], key=lambda x: x["offset"]):
                c = self.clips[cl["clip"]]
                ref = self.asset(cl["clip"])
                if cl["offset"] - pos > 1 / 48:
                    inner += f'<gap name="Gap" offset="{rt(pos)}" start="0s" duration="{rt(cl["offset"] - pos)}"/>'
                    pos = cl["offset"]
                fmt = self._format(c.width, c.height, c.fps_label) if c.fps_num else self.seq_fmt
                inner += (f'<asset-clip ref="{ref}" name={quoteattr(c.name)} offset="{rt(pos)}" start="0s" '
                          f'duration="{rt(c.duration)}" format="{fmt}" audioRole={quoteattr(a.get("audio_role", "dialogue"))}/>')
                pos += c.duration
            angles.append(f'<mc-angle name={quoteattr(a["name"])} angleID="{aid}">{inner}</mc-angle>')
            a["angle_id"] = aid
        self.res.append(f'<media id="{rid}" name={quoteattr(mc["name"])}><multicam format="{self.seq_fmt}" tcStart="0s" tcFormat="NDF">{"".join(angles)}</multicam></media>')
        self.mc_ids[mc["id"]] = rid
        self.mc_meta[mc["id"]] = mc
        return rid

    # ---------- clips in a timeline ----------
    def _markers(self, markers, clip_start_s, fps=SEQ_FPS):
        out = []
        for m in markers or []:
            t = rt(clip_start_s + m["t"], fps)
            if m.get("todo"):
                out.append(f'<marker start="{t}" duration="{rt_frames(1)}" value={quoteattr(m["name"])} completed="0"/>')
            elif m.get("chapter"):
                out.append(f'<chapter-marker start="{t}" duration="{rt_frames(1)}" value={quoteattr(m["name"])}/>')
            else:
                out.append(f'<marker start="{t}" duration="{rt_frames(1)}" value={quoteattr(m["name"])}/>')
        return "".join(out)

    def clip_xml(self, item: dict, offset_s: float, lane: int | None = None, children: str = "") -> str:
        """item: {clip, in, out, name?, role?, slowmo?, gain_db?, fade_in?, fade_out?, markers?, mc?, angle?}"""
        c = self.clips[item["clip"]]
        dur_s = item["out"] - item["in"]
        lane_attr = f' lane="{lane}"' if lane else ""
        name = item.get("name") or c.name
        role = item.get("role")
        body = children
        # slow motion: source runs at a higher frame rate than the sequence
        if item.get("slowmo") and c.fps_num:
            src_fps = Fraction(c.fps_num, c.fps_den)
            factor = float(src_fps / SEQ_FPS)  # e.g. 2.5 for 59.94 -> 23.976
            tl_dur = dur_s * factor
            if c.fps_label in CONFORM_OK:
                body = f'<conform-rate scaleEnabled="1" srcFrameRate="{c.fps_label}"/>' + body
                conform_src = True
            else:
                body = (f'<timeMap><timept time="0s" value="{rt(item["in"], src_fps)}" interp="smooth2"/>'
                        f'<timept time="{rt(tl_dur)}" value="{rt(item["out"], src_fps)}" interp="smooth2"/></timeMap>') + body
        else:
            tl_dur = dur_s
        conform_src = locals().get("conform_src", False)
        if item.get("gain_db") is not None or item.get("fade_in") or item.get("fade_out"):
            fi = f'<fadeIn type="easeIn" duration="{rt(item["fade_in"])}"/>' if item.get("fade_in") else ""
            fo = f'<fadeOut type="easeOut" duration="{rt(item["fade_out"])}"/>' if item.get("fade_out") else ""
            inner_p = f'<param name="amount">{fi}{fo}</param>' if (fi or fo) else ""
            body = f'<adjust-volume amount="{item.get("gain_db", 0):.1f}dB">{inner_p}</adjust-volume>' + body
        body += self._markers(item.get("markers"), item["in"])
        fades = ""
        role_attrs = ""
        if role:
            if c.kind == "audio" or role in ("music", "effects") or role.startswith(("music", "effects", "dialogue")):
                role_attrs += f" audioRole={quoteattr(role)}"
            else:
                role_attrs += f" videoRole={quoteattr(role)}"
        if item.get("video_role"):
            role_attrs += f" videoRole={quoteattr(item['video_role'])}"
        if item.get("audio_role"):
            role_attrs += f" audioRole={quoteattr(item['audio_role'])}"
        if item.get("mc"):
            mc = self.mc_meta[item["mc"]]
            ref = self.mc_ids[item["mc"]]
            angle = next(a for a in mc["angles"] if any(cl["clip"] == item["clip"] for cl in a["clips"]))
            cl = next(cl for cl in angle["clips"] if cl["clip"] == item["clip"])
            start_in_mc = item["in"] + cl["offset"]
            return (f'<mc-clip ref="{ref}" name={quoteattr(name)}{lane_attr} offset="{rt(offset_s)}" start="{rt(start_in_mc)}" duration="{rt(tl_dur)}">'
                    f'<mc-source angleID="{angle["angle_id"]}" srcEnable="all"/>{body}</mc-clip>')
        ref = self.asset(item["clip"])
        src_fps = Fraction(c.fps_num, c.fps_den) if c.fps_num else None
        start = rt(item["in"], src_fps) if src_fps else rt_samples(item["in"], c.audio_rate)
        fmt = f' format="{self._format(c.width, c.height, c.fps_label)}"' if c.fps_num else ""
        dur_attr = rt(dur_s, src_fps) if conform_src else rt(tl_dur)
        return (f'<asset-clip ref="{ref}" name={quoteattr(name)}{lane_attr} offset="{rt(offset_s)}" start="{start}" duration="{dur_attr}"{fmt}{role_attrs}>'
                f'{body}</asset-clip>')

    def parent_start(self, item: dict) -> float:
        if item.get("gap"):
            return 0.0
        if item.get("mc"):
            mc = self.mc_meta[item["mc"]]
            cl = next(cl for a in mc["angles"] for cl in a["clips"] if cl["clip"] == item["clip"])
            return item["in"] + cl["offset"]
        return item.get("in", 0.0)

    # ---------- project ----------
    def project_xml(self) -> str:
        p = self.plan
        spine = sorted(p.get("spine", []), key=lambda x: x["at"])
        connected = sorted(p.get("connected", []), key=lambda x: x["at"])
        # Attach each connected item to the primary element it starts over.
        prim = []
        for s in spine:
            prim.append({"at": s["at"], "dur": s["dur"], "item": s, "kids": []})
        for citem in connected:
            host = None
            for e in prim:
                if e["at"] <= citem["at"] < e["at"] + e["dur"] - 1e-6:
                    host = e
                    break
            if host is None:
                host = min(prim, key=lambda e: abs(e["at"] - citem["at"])) if prim else None
            if host is None:
                continue
            host["kids"].append(citem)
        parts = []
        for e in prim:
            s = e["item"]
            ps = self.parent_start(s)
            kids_xml = "".join(self.clip_xml(k, k["at"] - e["at"] + ps, lane=k.get("lane", 1)) for k in e["kids"])
            if s.get("gap"):
                parts.append(f'<gap name="Gap" offset="{rt(s["at"])}" start="0s" duration="{rt(s["dur"])}">{kids_xml}{self._markers(s.get("markers"), 0.0)}</gap>')
            else:
                parts.append(self.clip_xml(s, s["at"], None, kids_xml))
        total = max((e["at"] + e["dur"] for e in prim), default=0.0)
        seq = (f'<sequence format="{self.seq_fmt}" duration="{rt(total)}" tcStart="{SEQ_START_TC}" tcFormat="NDF" audioLayout="stereo" audioRate="48k">'
               f'<spine>{"".join(parts)}</spine></sequence>')
        return f'<project name={quoteattr(p["name"])}>{seq}</project>'

    # ---------- event ----------
    def event_clips_xml(self) -> str:
        p = self.plan
        out = []
        kw = p.get("keywords", {})
        rej = set(p.get("rejected", []))
        notes = p.get("notes", {})
        roles = p.get("roles", {})
        for path, c in self.clips.items():
            if path not in p.get("event_clips", list(self.clips.keys())):
                continue
            ref = self.asset(path)
            fps = Fraction(c.fps_num, c.fps_den) if c.fps_num else None
            dur = rt(c.duration, fps) if fps else rt_samples(c.duration, c.audio_rate)
            inner = f"<note>{escape(notes[path])}</note>" if notes.get(path) else ""
            for k in kw.get(path, []):
                inner += f'<keyword start="0s" duration="{dur}" value={quoteattr(k)}/>'
            if path in rej:
                inner += f'<rating start="0s" duration="{dur}" value="reject" note={quoteattr(notes.get(path, ""))}/>'
            role_attr = ""
            r = roles.get(path)
            if r:
                role_attr = f" audioRole={quoteattr(r)}" if (c.kind == "audio" or r.startswith(("dialogue", "music", "effects"))) else f" videoRole={quoteattr(r)}"
                if c.kind == "video" and r.startswith("dialogue") and p.get("video_roles", {}).get(path):
                    role_attr += f" videoRole={quoteattr(p['video_roles'][path])}"
            elif p.get("video_roles", {}).get(path):
                role_attr = f" videoRole={quoteattr(p['video_roles'][path])}"
            fmt = f' format="{self._format(c.width, c.height, c.fps_label)}"' if c.fps_num else ""
            out.append(f'<asset-clip ref="{ref}" name={quoteattr(c.name)} offset="0s" start="0s" duration="{dur}"{fmt}{role_attr}>{inner}</asset-clip>')
        return "".join(out)

    def write(self, out_path: str) -> str:
        p = self.plan
        for mc in p.get("multicams", []):
            self.multicam(mc)
        project = self.project_xml() if p.get("spine") else ""
        event_clips = self.event_clips_xml() if p.get("include_event_clips", True) else ""
        mc_event = "".join(f'<mc-clip ref="{self.mc_ids[m["id"]]}" name={quoteattr(m["name"])} offset="0s" start="0s" duration="{rt(m.get("duration", 0))}"/>' for m in p.get("multicams", []) if m.get("duration"))
        lib = f' location={quoteattr(file_url(p["library"]))}' if p.get("library") else ""
        xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n<fcpxml version="1.11">'
               f'<resources>{"".join(self.res)}</resources>'
               f'<library{lib}><event name={quoteattr(p["event"])}>{project}{mc_event}{event_clips}</event></library></fcpxml>')
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(xml, encoding="utf-8")
        validate(out_path)
        return out_path


def validate(path: str) -> bool | None:
    """Validate against Apple's FCPXML 1.11 DTD when xmllint and the DTD are available (setup-kit fetches it)."""
    import os, shutil, subprocess
    dtd = os.environ.get("BUWAN_FCPXML_DTD") or os.path.join(os.path.expanduser("~"), ".buwan", "dtd", "FCPXMLv1_11.dtd")
    if not (shutil.which("xmllint") and os.path.exists(dtd)):
        return None
    r = subprocess.run(["xmllint", "--noout", "--dtdvalid", dtd, path], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FCPXML DTD validation FAILED for {path}:\n{r.stderr[:1500]}", file=__import__('sys').stderr)
        return False
    return True


def write_plan(plan: dict, out_path: str) -> str:
    return Writer(plan).write(out_path)
