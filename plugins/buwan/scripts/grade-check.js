#!/usr/bin/env node
// Buwan grade check — measures a graded export (or stills) against the studio look targets,
// so every editor's grade lands in the same place regardless of app.
//
//   node grade-check.js check <video|folder-of-stills> --look warm|cool|bw [--targets file.json] [--every 2]
//   node grade-check.js calibrate <folder of reference stills> --look warm|cool|bw [--targets file.json]
//
// Measures with ffmpeg signalstats (8-bit video levels 16-235):
//   black   = 10th-percentile luma (YLOW)    lifted, never crushed
//   white   = 90th-percentile luma (YHIGH)   soft highlights, never clipped
//   bright  = average luma (YAVG)
//   sat     = average saturation (SATAVG)     muted
//   hue     = average hue (HUEAVG, degrees)   warm vs cool
// Exit: 0 PASS, 1 FAIL, 2 error.
const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

const args = process.argv.slice(2);
const [cmd, input] = args;
const opt = (n, d) => { const i = args.indexOf(`--${n}`); return i >= 0 ? args[i + 1] : d; };
const look = (opt("look", "warm") || "warm").toLowerCase();
const defaultTargets = path.join(__dirname, "..", "kit", "grade", "targets.json");
const targetsFile = opt("targets", fs.existsSync(path.join(process.cwd(), "kit", "grade", "targets.json")) ? path.join(process.cwd(), "kit", "grade", "targets.json") : defaultTargets);
const every = parseFloat(opt("every", "2"));
const METRICS = { black: "YLOW", white: "YHIGH", bright: "YAVG", sat: "SATAVG", hue: "HUEAVG" };

if (!cmd || !input || !["check", "calibrate"].includes(cmd)) {
  console.log(fs.readFileSync(__filename, "utf8").split("\n").slice(1, 15).map((l) => l.replace(/^\/\/ ?/, "")).join("\n"));
  process.exit(cmd ? 2 : 0);
}
if (!fs.existsSync(input)) { console.log(`Not found: ${input}`); process.exit(2); }

function measure(file, isStill) {
  const vf = (isStill ? "" : `fps=1/${every},`) + "scale=640:-2,signalstats,metadata=print:file=-";
  const r = spawnSync("ffmpeg", ["-v", "error", "-i", file, "-vf", vf, "-f", "null", "-"], { encoding: "utf8", maxBuffer: 1 << 28 });
  if (r.status !== 0) throw new Error(`ffmpeg failed on ${file}: ${r.stderr}`);
  const frames = [];
  let cur = null;
  for (const line of r.stdout.split(/\r?\n/)) {
    const f = line.match(/^frame:\d+\s+pts:\S+\s+pts_time:(\S+)/);
    if (f) { cur = { t: parseFloat(f[1]), file }; frames.push(cur); continue; }
    const m = line.match(/^lavfi\.signalstats\.(\w+)=(\S+)/);
    if (m && cur) cur[m[1]] = parseFloat(m[2]);
  }
  return frames.map((fr) => Object.fromEntries([["t", fr.t], ["file", fr.file], ...Object.entries(METRICS).map(([k, s]) => [k, fr[s]])]));
}

function collect(p) {
  const st = fs.statSync(p);
  if (st.isDirectory()) {
    const files = fs.readdirSync(p).filter((f) => /\.(png|jpe?g|tiff?|dpx|exr)$/i.test(f)).map((f) => path.join(p, f));
    if (!files.length) throw new Error(`No stills in ${p}`);
    return files.flatMap((f) => measure(f, true));
  }
  return measure(p, /\.(png|jpe?g|tiff?)$/i.test(p));
}

const median = (a) => { const s = [...a].sort((x, y) => x - y); return s[Math.floor(s.length / 2)]; };
const pct = (a, q) => { const s = [...a].sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.max(0, Math.round(q * (s.length - 1))))]; };
const tc = (t) => { const s = Math.floor(t); return `${String(Math.floor(s / 3600)).padStart(2, "0")}:${String(Math.floor(s / 60) % 60).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`; };

try {
  const frames = collect(input);
  if (!frames.length) throw new Error("No frames measured.");
  const all = fs.existsSync(targetsFile) ? JSON.parse(fs.readFileSync(targetsFile, "utf8")) : {};

  if (cmd === "calibrate") {
    const t = { source: path.resolve(input), calibrated: new Date().toISOString().slice(0, 10), frames: frames.length };
    for (const k of Object.keys(METRICS)) {
      const v = frames.map((f) => f[k]).filter((x) => !Number.isNaN(x));
      const lo = pct(v, 0.1), hi = pct(v, 0.9), pad = k === "hue" ? 15 : Math.max(4, (hi - lo) * 0.25);
      t[k] = [+(lo - pad).toFixed(1), +(hi + pad).toFixed(1)];
    }
    if (look === "bw") t.hue = null;
    all[look] = t;
    fs.mkdirSync(path.dirname(targetsFile), { recursive: true });
    fs.writeFileSync(targetsFile, JSON.stringify(all, null, 2));
    console.log(`Calibrated "${look}" from ${frames.length} reference frames -> ${targetsFile}`);
    console.log(JSON.stringify(t, null, 2));
    process.exit(0);
  }

  const T = all[look];
  if (!T) throw new Error(`No targets for look "${look}" in ${targetsFile}`);
  const rows = [];
  let fails = 0;
  for (const k of Object.keys(METRICS)) {
    if (!T[k]) continue;
    const v = frames.map((f) => f[k]).filter((x) => !Number.isNaN(x));
    const m = median(v);
    const [lo, hi] = T[k];
    const pass = m >= lo && m <= hi;
    const out = frames.filter((f) => f[k] < lo || f[k] > hi);
    if (!pass) fails++;
    rows.push([k, `${lo}-${hi}`, m.toFixed(1), pass ? "PASS" : "FAIL", out.length ? `${out.length}/${frames.length} frames off, e.g. ${out.slice(0, 5).map((f) => (frames.length > 1 && !/\.(png|jpe?g|tiff?)$/i.test(f.file) ? tc(f.t) : path.basename(f.file))).join(" ")}` : ""]);
  }
  const clip = frames.filter((f) => f.white > 235 || f.black < 16).length;
  rows.push(["clipping", "none", `${clip} frames`, clip ? "WARN" : "PASS", clip ? "highlights over 235 or blacks under 16" : ""]);

  console.log(`BUWAN GRADE CHECK  ${input}  look=${look}  (${frames.length} frames${T.source ? `, targets from ${path.basename(T.source)}` : ", starting targets"})`);
  console.log("Measure".padEnd(10) + "Target".padEnd(14) + "Median".padEnd(9) + "Verdict ".padEnd(9) + "Where");
  for (const r of rows) console.log(r[0].padEnd(10) + r[1].padEnd(14) + r[2].padEnd(9) + r[3].padEnd(9) + r[4]);
  console.log(fails ? `\nGRADE: FAIL (${fails}). Adjust toward the Buwan look, or note an override in the paper edit.` : "\nGRADE: PASS");
  process.exit(fails ? 1 : 0);
} catch (e) {
  console.log(`grade-check: ${e.message}`);
  process.exit(2);
}
