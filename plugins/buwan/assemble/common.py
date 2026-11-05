"""Shared helpers for the Buwan assemble engine: ffprobe, time math, paths."""
from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from fractions import Fraction
from pathlib import Path
from typing import Optional

VIDEO_EXT = {".mp4", ".mov", ".mxf", ".m4v", ".mts", ".m2ts", ".avi", ".mkv", ".braw", ".crm"}
AUDIO_EXT = {".wav", ".aif", ".aiff", ".mp3", ".m4a", ".flac", ".aac"}
SEQ_FPS = Fraction(24000, 1001)  # the house timeline: 23.976 NDF
SEQ_START_TC = "86486400/24000s"  # 01:00:00:00 at 23.976 (exact)


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def run(cmd: list[str], check=True, capture=True, timeout=None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, capture_output=capture, text=True, timeout=timeout)


def ffprobe(path: str | Path) -> dict:
    r = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)])
    return json.loads(r.stdout)


def parse_rate(s: str) -> Fraction:
    if not s or s in ("0/0", "0"):
        return Fraction(0)
    if "/" in s:
        n, d = s.split("/")
        return Fraction(int(n), int(d)) if int(d) else Fraction(0)
    return Fraction(s)


def nominal_fps(fr: Fraction) -> tuple[str, Fraction]:
    """Snap a measured frame rate to a broadcast nominal. Returns (label, exact Fraction)."""
    table = [
        ("23.98", Fraction(24000, 1001)), ("24", Fraction(24)), ("25", Fraction(25)),
        ("29.97", Fraction(30000, 1001)), ("30", Fraction(30)), ("48", Fraction(48)), ("50", Fraction(50)),
        ("59.94", Fraction(60000, 1001)), ("60", Fraction(60)), ("119.88", Fraction(120000, 1001)), ("120", Fraction(120)),
    ]
    f = float(fr)
    best = min(table, key=lambda t: abs(float(t[1]) - f))
    return best


@dataclass
class Clip:
    path: str
    name: str
    kind: str  # video | audio
    duration: float
    fps_label: str = ""
    fps_num: int = 0
    fps_den: int = 1
    width: int = 0
    height: int = 0
    has_audio: bool = False
    audio_rate: int = 48000
    audio_channels: int = 2
    created: str = ""  # ISO from container metadata, may be wrong (camera clock)
    camera: str = ""  # top-level folder under the footage root
    rel: str = ""     # path relative to footage root
    codec: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def fps(self) -> Fraction:
        return Fraction(self.fps_num, self.fps_den) if self.fps_num else Fraction(0)

    def to_json(self):
        return asdict(self)

    @staticmethod
    def from_json(d):
        return Clip(**d)


def probe_clip(path: Path, root: Path) -> Optional[Clip]:
    try:
        info = ffprobe(path)
    except Exception as e:  # unreadable file
        log(f"ffprobe failed: {path}: {e}")
        return None
    fmt = info.get("format", {})
    v = next((s for s in info.get("streams", []) if s.get("codec_type") == "video" and s.get("disposition", {}).get("attached_pic", 0) == 0), None)
    a = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)
    dur = float(fmt.get("duration") or (v or a or {}).get("duration") or 0)
    rel = str(path.relative_to(root)) if root in path.parents or path == root else path.name
    camera = rel.split(os.sep)[0] if os.sep in rel else ""
    created = fmt.get("tags", {}).get("creation_time") or (v or {}).get("tags", {}).get("creation_time") or ""
    c = Clip(path=str(path), name=path.stem, kind="video" if v else "audio", duration=dur, created=created, camera=camera, rel=rel)
    if v:
        fr = parse_rate(v.get("r_frame_rate", "")) or parse_rate(v.get("avg_frame_rate", ""))
        label, exact = nominal_fps(fr) if fr else ("", Fraction(0))
        c.fps_label, c.fps_num, c.fps_den = label, exact.numerator, exact.denominator
        c.width, c.height = int(v.get("width", 0)), int(v.get("height", 0))
        c.codec = v.get("codec_name", "")
        rot = 0
        for sd in v.get("side_data_list", []) or []:
            if "rotation" in sd:
                rot = int(sd["rotation"])
        if rot in (90, -90, 270, -270):
            c.width, c.height = c.height, c.width
    if a:
        c.has_audio = True
        c.audio_rate = int(a.get("sample_rate", 48000))
        c.audio_channels = int(a.get("channels", 2))
        if not v:
            c.codec = a.get("codec_name", "")
    return c


def scan_media(root: Path) -> list[Clip]:
    clips = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and not p.name.startswith(".") and p.suffix.lower() in VIDEO_EXT | AUDIO_EXT:
            c = probe_clip(p, root)
            if c and c.duration > 0:
                clips.append(c)
    return clips


# ---------- rational time on the sequence grid ----------
def frames(seconds: float, fps: Fraction = SEQ_FPS) -> int:
    return int(round(seconds * fps))


def rt(seconds: float, fps: Fraction = SEQ_FPS) -> str:
    """Seconds -> FCPXML rational string snapped to the frame grid of fps."""
    n = frames(seconds, fps)
    return rt_frames(n, fps)


def rt_frames(n: int, fps: Fraction = SEQ_FPS) -> str:
    # n frames = n * (den/num) seconds -> "(n*den)/num s"
    num, den = fps.numerator, fps.denominator
    return f"{n * den}/{num}s" if n else "0s"


def rt_samples(seconds: float, rate: int) -> str:
    n = int(round(seconds * rate))
    return f"{n}/{rate}s" if n else "0s"


def file_url(path: str | Path) -> str:
    from urllib.parse import quote
    p = str(Path(path).resolve())
    return "file://" + quote(p, safe="/:@&+$,;=!*'()")


def tc(seconds: float, fps: Fraction = SEQ_FPS, base: float = 3600.0) -> str:
    """Record timecode string (NDF) for display, offset by base (01:00:00:00)."""
    r = round(fps)
    f = frames(seconds, fps) + int(round(base * r))  # NDF: timecode counts nominal frames, 01:00:00:00 = 3600*24
    ff = f % r
    s = f // r
    return f"{s // 3600:02d}:{(s // 60) % 60:02d}:{s % 60:02d}:{ff:02d}"


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def load_json(p):
    with open(p) as f:
        return json.load(f)


def save_json(p, obj):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump(obj, f, indent=1)
