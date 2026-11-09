"""Look: build a studio look LUT that makes this wedding's footage match a reference film.

  reference film (the studio's finished SDE)  ->  frames, letterbox cropped; black, title and B&W frames skipped
  this wedding's footage                      ->  one frame per sampled clip, with its exposure fix applied
  match, in CIE Lab:
    - tone: the lightness distribution (CDF) of the footage mapped onto the reference's (film contrast,
      lifted blacks, highlight roll-off), smoothed and kept monotone;
    - color: in 5 lightness bands, the a/b mean (split toning) and spread (saturation) matched, blended
      smoothly across bands; a/b spread is never pushed up more than MAX_SAT_UP (no neon skin).
  -> a 33-point .cube (Rec.709 in/out) and a before / after / reference contact sheet to check by eye.

Nothing is re-encoded here; the LUT is applied by `assemble.js enhance-render` (or loaded in the editing app).
"""
from __future__ import annotations

import json
import random
import warnings
import subprocess
from pathlib import Path

import numpy as np

from common import Clip, log

warnings.filterwarnings("ignore", category=RuntimeWarning, module=__name__)   # numpy/Accelerate matmul noise on macOS

N_GRID = 33
BANDS = 5
MAX_SAT_UP = 1.10
SKIP_DARK = 22.0     # mean L* below this: black / title frame
SKIP_GRAY = 3.0      # mean chroma below this: B&W frame
TONE_MIX = 0.7       # how much of the reference's tone curve to take (1.0 = all; dark, letterboxed films crush whites)
WHITE_OUT = 95.0     # L* 100 lands here: a soft film shoulder, whites stay white
SHOULDER_FROM = 80.0 # above this the curve blends into the shoulder
PROTECT_WHITES = (82.0, 98.0)  # color shifts fade out across this L* range (no tinted, banded gowns or skies)


# ---------- color math (Rec.709 / sRGB-ish display values, D65) ----------
def _lin(v):
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def _gam(v):
    v = np.clip(v, 0, 1)
    return np.where(v <= 0.0031308, v * 12.92, 1.055 * v ** (1 / 2.4) - 0.055)


_M = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
_MI = np.linalg.inv(_M)
_WP = np.array([0.95047, 1.0, 1.08883])


def rgb_to_lab(rgb):
    xyz = _lin(rgb) @ _M.T / _WP
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def lab_to_rgb(lab):
    fy = (lab[..., 0] + 16) / 116
    fx, fz = fy + lab[..., 1] / 500, fy - lab[..., 2] / 200
    f = np.stack([fx, fy, fz], -1)
    xyz = np.where(f ** 3 > 216 / 24389, f ** 3, (116 * f - 16) / (24389 / 27)) * _WP
    return _gam(xyz @ _MI.T)


# ---------- frames ----------
def _frame(path: str, t: float, w: int = 320) -> np.ndarray | None:
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", path, "-frames:v", "1", "-vf", f"scale={w}:-2,format=rgb24",
                        "-f", "rawvideo", "-"], capture_output=True)
    if r.returncode or not r.stdout:
        return None
    h = len(r.stdout) // (w * 3)
    return np.frombuffer(r.stdout[: w * h * 3], np.uint8).reshape(h, w, 3).astype(np.float32) / 255


def _crop_bars(img: np.ndarray) -> np.ndarray:
    rows = img.mean(axis=(1, 2)) > 0.03
    if rows.sum() < img.shape[0] * 0.4:
        return img
    idx = np.where(rows)[0]
    return img[idx[0] + 2: idx[-1] - 1]


def _usable(lab: np.ndarray) -> bool:
    return lab[..., 0].mean() > SKIP_DARK and np.hypot(lab[..., 1], lab[..., 2]).mean() > SKIP_GRAY


def reference_frames(video: Path, every_s: float = 2.0) -> list[np.ndarray]:
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                               capture_output=True, text=True).stdout.strip() or 0)
    out = []
    t = 1.0
    while t < dur - 1:
        f = _frame(str(video), t)
        if f is not None:
            lab = rgb_to_lab(_crop_bars(f))
            if _usable(lab):
                out.append(lab.reshape(-1, 3))
        t += every_s
    return out


def footage_frames(clips: list[Clip], exposure: dict, n: int = 240, seed: int = 7) -> list[np.ndarray]:
    vids = [c for c in clips if c.kind == "video" and c.duration > 1.5]
    random.Random(seed).shuffle(vids)
    out = []
    for c in vids:
        if len(out) >= n:
            break
        f = _frame(c.path, c.duration * 0.4)
        if f is None:
            continue
        ev = (exposure.get(c.path) or {}).get("ev") or 0.0
        if ev:
            f = _gam(_lin(f) * 2 ** ev)
        lab = rgb_to_lab(f)
        if _usable(lab):
            out.append(lab.reshape(-1, 3))
    return out


# ---------- the match ----------
def _tone_curve(src_L: np.ndarray, ref_L: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    qs = np.linspace(0.002, 0.998, 200)
    s, r = np.quantile(src_L, qs), np.quantile(ref_L, qs)
    s, r = np.maximum.accumulate(s), np.maximum.accumulate(r)
    xs = np.concatenate([[0], s, [100]])
    ys = np.concatenate([[min(r[0], s[0])], r, [max(r[-1], 96)]])
    k = np.ones(9) / 9   # smooth the curve, keep it monotone
    ys = np.convolve(np.pad(ys, 4, mode="edge"), k, mode="valid")
    ys = np.maximum.accumulate(ys)
    xs, idx = np.unique(xs, return_index=True)
    ys = ys[idx]
    ys = xs + TONE_MIX * (ys - xs)                       # take part of the reference's contrast
    shoulder = SHOULDER_FROM + (WHITE_OUT - SHOULDER_FROM) * (1 - np.exp(-(xs - SHOULDER_FROM) / 12.0)) / (1 - np.exp(-(100 - SHOULDER_FROM) / 12.0))
    t = np.clip((xs - SHOULDER_FROM) / (100 - SHOULDER_FROM), 0, 1)
    ys = np.where(xs > SHOULDER_FROM, np.maximum(ys, (1 - t) * ys + t * shoulder), ys)
    return xs, np.maximum.accumulate(ys)


def _band_weights(L: np.ndarray) -> np.ndarray:
    centers = np.linspace(10, 90, BANDS)
    w = np.exp(-((L[..., None] - centers) / 14.0) ** 2)
    return w / (w.sum(-1, keepdims=True) + 1e-9)


def build(src: list[np.ndarray], ref: list[np.ndarray]) -> dict:
    S, R = np.concatenate(src), np.concatenate(ref)
    xs, ys = _tone_curve(S[:, 0], R[:, 0])
    Smapped = np.interp(S[:, 0], xs, ys)
    stats = []
    ws, wr = _band_weights(Smapped), _band_weights(R[:, 0])
    for b in range(BANDS):
        a = ws[:, b][:, None]
        c = wr[:, b][:, None]
        sm = (S[:, 1:] * a).sum(0) / a.sum()
        rm = (R[:, 1:] * c).sum(0) / c.sum()
        ss = np.sqrt(((S[:, 1:] - sm) ** 2 * a).sum(0) / a.sum())
        rs = np.sqrt(((R[:, 1:] - rm) ** 2 * c).sum(0) / c.sum())
        stats.append({"src_mean": sm.tolist(), "ref_mean": rm.tolist(), "scale": np.minimum(rs / np.maximum(ss, 1e-3), MAX_SAT_UP).tolist()})
    return {"tone_x": xs.tolist(), "tone_y": ys.tolist(), "bands": stats}


def apply_lab(lab: np.ndarray, model: dict, strength: float = 1.0) -> np.ndarray:
    L = np.interp(lab[..., 0], model["tone_x"], model["tone_y"])
    w = _band_weights(L)
    sm = np.einsum("...b,bc->...c", w, np.array([b["src_mean"] for b in model["bands"]]))
    rm = np.einsum("...b,bc->...c", w, np.array([b["ref_mean"] for b in model["bands"]]))
    sc = np.einsum("...b,bc->...c", w, np.array([b["scale"] for b in model["bands"]]))
    ab = (lab[..., 1:] - sm) * sc + rm
    lo, hi = PROTECT_WHITES
    keep = np.clip((L - lo) / (hi - lo), 0, 1)[..., None]
    keep = keep * keep * (3 - 2 * keep)                  # smoothstep: near-whites keep their own color
    ab = ab + (lab[..., 1:] - ab) * keep
    out = np.concatenate([L[..., None], ab], -1)
    return lab + (out - lab) * strength


def write_cube(path: Path, model: dict, title: str, strength: float = 1.0) -> None:
    g = np.linspace(0, 1, N_GRID)
    b, gg, r = np.meshgrid(g, g, g, indexing="ij")          # .cube order: red fastest
    rgb = np.stack([r, gg, b], -1).reshape(-1, 3)
    out = np.clip(lab_to_rgb(apply_lab(rgb_to_lab(rgb), model, strength)), 0, 1)
    with open(path, "w") as f:
        f.write(f'TITLE "{title}"\nLUT_3D_SIZE {N_GRID}\nDOMAIN_MIN 0.0 0.0 0.0\nDOMAIN_MAX 1.0 1.0 1.0\n')
        for v in out:
            f.write(f"{v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")


def preview(path: Path, clips: list[Clip], exposure: dict, model: dict, reference: Path, n: int = 8, strength: float = 1.0) -> None:
    """Rows: footage before | after (exposure + look) | a reference frame. One sheet to judge by eye."""
    from PIL import Image
    vids = [c for c in clips if c.kind == "video" and c.duration > 1.5]
    random.Random(11).shuffle(vids)
    rows = []
    for c in vids:
        if len(rows) >= n:
            break
        f = _frame(c.path, c.duration * 0.5, 480)
        if f is None:
            continue
        ev = (exposure.get(c.path) or {}).get("ev") or 0.0
        fe = _gam(_lin(f) * 2 ** ev) if ev else f
        after = np.clip(lab_to_rgb(apply_lab(rgb_to_lab(fe), model, strength)), 0, 1)
        rows.append(np.concatenate([f, after], 1))
    h = min(r.shape[0] for r in rows)
    sheet = np.concatenate([r[:h] for r in rows], 0)
    Image.fromarray((sheet * 255).astype(np.uint8)).save(path, quality=85)
    log(f"look preview: {path}")


def run(project: Path, clips: list[Clip], reference: Path, name: str, out_dir: Path, strength: float = 1.0) -> dict:
    adir = project / "edit" / "assemble"
    exposure = json.loads((adir / "exposure.json").read_text()) if (adir / "exposure.json").exists() else {}
    cache = project / "edit" / "grade" / f".{name}_frames.npz"
    if cache.exists():
        z = np.load(cache, allow_pickle=True)
        ref, src = list(z["ref"]), list(z["src"])
        log(f"look: reusing {len(ref)} reference and {len(src)} footage frames ({cache.name})")
    else:
        log(f"look: reading the reference {reference.name}")
        ref = reference_frames(reference)
        log(f"look: {len(ref)} usable reference frames; sampling this wedding's footage")
        src = footage_frames(clips, exposure)
        cache.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(cache, ref=np.array(ref, dtype=object), src=np.array(src, dtype=object))
    log(f"look: {len(src)} footage frames")
    if len(ref) < 20 or len(src) < 40:
        raise SystemExit("not enough usable frames to build a look")
    model = build(src, ref)
    out_dir.mkdir(parents=True, exist_ok=True)
    cube = out_dir / f"{name}.cube"
    write_cube(cube, model, name, strength)
    (adir / "look.json").write_text(json.dumps({"name": name, "reference": str(reference), "strength": strength, "cube": str(cube), "model": model}, indent=1))
    preview(project / "edit" / "grade" / f"{name}_preview.jpg", clips, exposure, model, reference, strength=strength)
    log(f"look: wrote {cube}")
    return {"cube": str(cube), "reference_frames": len(ref), "footage_frames": len(src)}
