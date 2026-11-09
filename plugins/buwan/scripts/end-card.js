#!/usr/bin/env node
// Buwan logo end card (kit 06.08) on an EXPORTED film: the card is conformed to the film's size and frame
// rate and appended after the last frame; the film's sound is kept and padded with silence under the card.
// (Inside an editing project use the app: Premiere bridge step `endcard`, or append the .mov by hand.)
//
//   node end-card.js append <film.mp4|mov> [--card <06.08 .mov>] [--out <file>] [--fade-tail <sec>]
//      --card       default: <workspace>/kit/wedding/06.08_logo-end-card.mov (cwd, then ~/Buwan, then ~/.buwan)
//      --out        default: <film>_endcard.mp4 next to the film (the film itself is never overwritten)
//      --fade-tail  fade the film's sound out over its last N seconds (default 0: the cut already ends right)
// Output: H.264 High, CRF 16, AAC 320k, Rec.709 tags. Needs ffmpeg/ffprobe on PATH.
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
if (args[0] !== "append" || !args[1]) {
  console.log(fs.readFileSync(__filename, "utf8").split("\n").slice(1, 11).map((l) => l.replace(/^\/\/ ?/, "")).join("\n"));
  process.exit(args.length ? 1 : 0);
}
const film = path.resolve(args[1]);
if (!fs.existsSync(film)) { console.error("film not found: " + film); process.exit(2); }
const cands = [opt("--card"), path.join(process.cwd(), "kit", "wedding", "06.08_logo-end-card.mov"),
  path.join(os.homedir(), "Buwan", "kit", "wedding", "06.08_logo-end-card.mov"),
  path.join(os.homedir(), ".buwan", "kit", "wedding", "06.08_logo-end-card.mov")].filter(Boolean);
const card = cands.find((p) => fs.existsSync(p));
if (!card) { console.error("06.08_logo-end-card.mov not found (run /buwan:setup-kit, or pass --card)"); process.exit(2); }
const out = path.resolve(opt("--out", film.replace(/\.[^.]+$/, "") + "_endcard.mp4"));
if (out === film) { console.error("--out must differ from the film"); process.exit(2); }

const probe = (f) => JSON.parse(spawnSync("ffprobe", ["-v", "error", "-show_streams", "-show_format", "-of", "json", f], { encoding: "utf8" }).stdout);
const pf = probe(film), pc = probe(card);
const v = pf.streams.find((s) => s.codec_type === "video");
const hasA = pf.streams.some((s) => s.codec_type === "audio");
const fdur = parseFloat(pf.format.duration), cdur = parseFloat(pc.format.duration);
const W = v.width, H = v.height, R = v.r_frame_rate;
const tail = parseFloat(opt("--fade-tail", "0")) || 0;

// the card fills the frame height (letterboxed films keep their bars: the card is black around the logo anyway)
const conform = `scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2:color=0x050504,setsar=1,fps=${R},format=yuv420p`;
const fc = [`[0:v]setsar=1,fps=${R},format=yuv420p[v0]`, `[1:v]${conform}[v1]`, `[v0][v1]concat=n=2:v=1:a=0[v]`];
if (hasA) fc.push(`[0:a]aresample=48000,aformat=channel_layouts=stereo${tail > 0 ? `,afade=t=out:st=${(fdur - tail).toFixed(3)}:d=${tail}` : ""},apad=whole_dur=${(fdur + cdur).toFixed(3)}[a]`);
else fc.push(`anullsrc=r=48000:cl=stereo,atrim=duration=${(fdur + cdur).toFixed(3)}[a]`);
const cmd = ["-v", "error", "-y", "-i", film, "-i", card, "-filter_complex", fc.join(";"), "-map", "[v]", "-map", "[a]",
  "-c:v", "libx264", "-profile:v", "high", "-crf", "16", "-preset", "slow", "-pix_fmt", "yuv420p",
  "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
  "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart", out];
console.log(`end card: ${path.basename(card)} (${cdur.toFixed(1)}s) after ${path.basename(film)} (${fdur.toFixed(1)}s, ${W}x${H} @ ${R})`);
const r = spawnSync("ffmpeg", cmd, { stdio: "inherit" });
if (r.status !== 0) process.exit(r.status || 1);
console.log(`wrote ${out}  (${(fdur + cdur).toFixed(1)}s)`);
