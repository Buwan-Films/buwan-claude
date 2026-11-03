#!/usr/bin/env node
// Buwan proof gate: measures an EDL against the house pacing targets.
// Usage: node proof-gate.js <file.edl> [--type wedding|corporate] [--mode speech|cut] [--fps 23.976]
// Exit code: 0 = all PASS, 1 = at least one FAIL, 2 = could not read the EDL.
const fs = require("fs");

const args = process.argv.slice(2);
const file = args.find((a) => !a.startsWith("--") && !/^(wedding|corporate|speech|cut|[\d.]+)$/.test(a));
const opt = (name, def) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 && args[i + 1] ? args[i + 1] : def;
};
const type = opt("type", /_corporate([\\/]|$)/i.test(file || "") ? "corporate" : "wedding");
const mode = opt("mode", "cut");
const fpsArg = parseFloat(opt("fps", "23.976"));
const tcBase = Math.round(fpsArg); // timecode counts frames at the rounded rate (NDF)
const realFps = Math.abs(fpsArg - 23.976) < 0.01 ? 24000 / 1001 : Math.abs(fpsArg - 29.97) < 0.01 ? 30000 / 1001 : fpsArg;

if (!file || !fs.existsSync(file)) {
  console.log(`proof-gate: EDL not found: ${file || "(none given)"}`);
  process.exit(2);
}

const tcToFrames = (tc) => {
  const [h, m, s, f] = tc.split(/[:;.]/).map(Number);
  return ((h * 60 + m) * 60 + s) * tcBase + f;
};
const secs = (frames) => frames / realFps;
const fmt = (s) => `${s.toFixed(2)}s`;
const tcOf = (frames) => {
  const f = frames % tcBase, t = Math.floor(frames / tcBase);
  const p = (n) => String(n).padStart(2, "0");
  return `${p(Math.floor(t / 3600))}:${p(Math.floor(t / 60) % 60)}:${p(t % 60)}:${p(f)}`;
};

// ---- parse CMX3600 ----
const lines = fs.readFileSync(file, "utf8").split(/\r?\n/);
const EV = /^\s*(\d{3,6})\s+(\S+)\s+(\S+)\s+(C|D|W\d{3}|K\s*[BO]?)\s*(\d{0,3})\s+(\d{2}[:;.]\d{2}[:;.]\d{2}[:;.]\d{2})\s+(\d{2}[:;.]\d{2}[:;.]\d{2}[:;.]\d{2})\s+(\d{2}[:;.]\d{2}[:;.]\d{2}[:;.]\d{2})\s+(\d{2}[:;.]\d{2}[:;.]\d{2}[:;.]\d{2})/i;
const events = [];
const parts = [];
let last = null;
for (const line of lines) {
  const m = line.match(EV);
  if (m) {
    last = { num: m[1], reel: m[2], track: m[3].toUpperCase(), recIn: tcToFrames(m[8]), recOut: tcToFrames(m[9]), name: "" };
    if (last.recOut > last.recIn) events.push(last);
    continue;
  }
  const clip = line.match(/^\*\s*FROM CLIP NAME:\s*(.+)$/i);
  if (clip && last) last.name = clip[1].trim();
  const part = line.match(/^\*\s*(?:PART\s*:?|LOC:.*?)\s*\b(Intro|Storyline|Ceremony|Outro)\b/i);
  if (part && last) parts.push({ name: part[1][0].toUpperCase() + part[1].slice(1).toLowerCase(), at: last.recIn });
}
if (!events.length) {
  console.log(`proof-gate: no CMX3600 events found in ${file}. Export the timeline as CMX3600 (V1 for picture).`);
  process.exit(2);
}

// Picture cut = video events; speech = whatever is there. Merge duplicates (same record in/out).
let pool = mode === "cut" ? events.filter((e) => /V/.test(e.track)) : events;
if (!pool.length) pool = events;
const seen = new Map();
for (const e of pool) seen.set(`${e.recIn}-${e.recOut}`, e);
const shots = [...seen.values()].sort((a, b) => a.recIn - b.recIn);
const durs = shots.map((e) => secs(e.recOut - e.recIn));
const total = secs(shots[shots.length - 1].recOut - shots[0].recIn);
const avg = durs.reduce((a, b) => a + b, 0) / durs.length;
const sorted = [...durs].sort((a, b) => a - b);
const median = sorted[Math.floor(sorted.length / 2)];

const rows = [];
const add = (rule, target, measured, verdict, where = "") => rows.push({ rule, target, measured, verdict, where });

add("Events measured", "-", `${shots.length} (${mode} mode, ${type})`, "INFO");
add("Total length", "-", `${fmt(total)} (${(total / 60).toFixed(1)} min)`, "INFO");
add("Average shot", "-", fmt(avg), "INFO");
add("Median shot", "-", fmt(median), "INFO");

const tiny = shots.filter((e, i) => durs[i] < (mode === "speech" ? 0.5 : 0.3));
add(
  mode === "speech" ? "No clipped lines (< 0.5s)" : "No flash frames (< 0.3s)",
  "0",
  String(tiny.length),
  tiny.length ? (mode === "speech" ? "FAIL" : "WARN") : "PASS",
  tiny.slice(0, 8).map((e) => `#${e.num}@${tcOf(e.recIn)}`).join(" ")
);

if (mode === "speech") {
  if (type === "wedding") {
    const targets = { Intro: [60, 90], Storyline: [120, 150], Outro: [120, 180] };
    if (parts.length) {
      parts.sort((a, b) => a.at - b.at);
      const end = shots[shots.length - 1].recOut;
      parts.forEach((p, i) => {
        const len = secs((parts[i + 1] ? parts[i + 1].at : end) - p.at);
        const t = targets[p.name];
        add(`${p.name} length (speech selects)`, t ? `${t[0]}-${t[1]}s` : "climax", fmt(len), t ? (len >= t[0] && len <= t[1] ? "PASS" : "WARN") : "INFO");
      });
    } else {
      add("4-part structure marked", "* PART: <name> comments", "none found", "WARN");
    }
  }
} else if (type === "wedding") {
  add("Average shot length", "2.5-3.0s (+/-10%)", fmt(avg), avg >= 2.25 && avg <= 3.3 ? "PASS" : "FAIL");

  const holds = shots.filter((e, i) => durs[i] >= 15);
  add("Holds (vows / first looks)", ">= 1 shot of 15-20s", `${holds.length}`, holds.length ? "PASS" : "FAIL", holds.map((e) => `#${e.num}@${tcOf(e.recIn)}`).join(" "));
  const long = shots.filter((e, i) => durs[i] > 20);
  add("Holds not over 20s", "<= 20s", long.length ? `${long.length} over` : "ok", long.length ? "WARN" : "PASS", long.map((e) => `#${e.num}@${tcOf(e.recIn)}`).join(" "));

  // Peak burst: most cuts starting inside any 30s window.
  let best = 0, bestAt = 0;
  for (let i = 0; i < shots.length; i++) {
    const limit = shots[i].recIn + 30 * realFps;
    let n = 0;
    for (let j = i; j < shots.length && shots[j].recIn < limit; j++) n++;
    if (n > best) (best = n), (bestAt = shots[i].recIn);
  }
  add("Peak burst (cuts in 30s)", ">= 15 (up to ~30)", String(best), best >= 15 ? (best > 32 ? "WARN" : "PASS") : "FAIL", `from ${tcOf(bestAt)}`);
  const burstShare = durs.filter((d) => d <= 2).length / durs.length;
  add("Share of 1-2s burst shots", "-", `${Math.round(burstShare * 100)}%`, "INFO");
  add("Film length (highlights)", "6-10 min", `${(total / 60).toFixed(1)} min`, total >= 360 && total <= 600 ? "PASS" : "WARN");
} else {
  add("Average shot length", "1.5-2.5s (+/-10%)", fmt(avg), avg >= 1.35 && avg <= 2.75 ? "PASS" : "FAIL");
  const steady = durs.filter((d) => d >= 1.5 && d <= 2.5).length / durs.length;
  add("Steady shots in 1.5-2.5s", "majority", `${Math.round(steady * 100)}%`, steady >= 0.5 ? "PASS" : "WARN");
  const holds = shots.filter((e, i) => durs[i] >= 6);
  add("Holds (speakers / keynote line)", "on speakers only", `${holds.length} shots >= 6s`, "INFO", holds.slice(0, 10).map((e) => `#${e.num} ${e.name || e.reel}`).join(" | "));
}

add("On beat and on words", "every cut", "not measurable (EDL)", "CHECK", "editor confirms by eye in review");

const w = (s, n) => String(s).padEnd(n);
console.log(`BUWAN PROOF GATE  ${file}`);
console.log(w("Rule", 34) + w("Target", 30) + w("Measured", 30) + w("Verdict", 8) + "Where");
for (const r of rows) console.log(w(r.rule, 34) + w(r.target, 30) + w(r.measured, 30) + w(r.verdict, 8) + r.where);
const fails = rows.filter((r) => r.verdict === "FAIL").length;
console.log(fails ? `\nGATE: FAIL (${fails} rule${fails > 1 ? "s" : ""}). Fix or write an override reason in the paper edit.` : "\nGATE: PASS (confirm beat/word timing by eye).");
process.exit(fails ? 1 : 0);
