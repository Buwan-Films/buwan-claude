#!/usr/bin/env node
// Buwan kit renderer — turns components from the Buwan Video Component Kit into
// app-neutral video clips (ProRes 4444 with alpha), with the job's real text.
// Same engine on every editor's machine, so graphics match across Premiere, Final Cut and Resolve.
//
//   node render-kit.js list                         all components (code, name, size, kind)
//   node render-kit.js texts <code>                 the sample text strings in a component
//   node render-kit.js render <code> [options]      render one clip
//      --text '{"Sample text":"Real text",...}'     or --text path/to/map.json
//      --out <file.mov>                             default ./<code>_<slug>.mov
//      --variant matte|edge|leak                    transitions only (03.03, 03.04, 03.05)
//      --hold <seconds>                             hold after the animation ends (default 2)
//      --still                                      also write a PNG of the final frame
//   node render-kit.js prerender <outdir>           render every text-free component + transition elements
//
// Needs: Node 18+, ffmpeg on PATH, Playwright + Chromium (installed by /buwan:setup-kit).
const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

const ROOT = path.join(__dirname, "..");
const KIT_HTML = path.join(ROOT, "reference", "video-kit.html");
const FONTS = path.join(ROOT, "kit", "fonts");
const FPS_NUM = 24000, FPS_DEN = 1001;

function loadPlaywright() {
  const tries = [
    "playwright",
    process.env.CLAUDE_PLUGIN_DATA && path.join(process.env.CLAUDE_PLUGIN_DATA, "node_modules", "playwright"),
    process.env.BUWAN_DEPS && path.join(process.env.BUWAN_DEPS, "node_modules", "playwright"),
    path.join(require("os").homedir(), ".buwan", "deps", "node_modules", "playwright"),
  ].filter(Boolean);
  for (const t of tries) {
    try { return require(t); } catch {}
  }
  console.error("Playwright is not installed. Run /buwan:setup-kit (it installs Playwright and Chromium).");
  process.exit(3);
}

const slug = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
const fileUrl = (p) => "file:///" + path.resolve(p).replace(/\\/g, "/").replace(/^\/+/, "");

const FONT_CSS = [
  ["Cormorant Garamond", "CormorantGaramond-Regular.ttf", 400, "normal"],
  ["Cormorant Garamond", "CormorantGaramond-Medium.ttf", 500, "normal"],
  ["Cormorant Garamond", "CormorantGaramond-SemiBold.ttf", 600, "normal"],
  ["Cormorant Garamond", "CormorantGaramond-Italic.ttf", 400, "italic"],
  ["Cormorant Garamond", "CormorantGaramond-MediumItalic.ttf", 500, "italic"],
  ["Cormorant Garamond", "CormorantGaramond-SemiBoldItalic.ttf", 600, "italic"],
  ["Cinzel", "Cinzel-Regular.ttf", 400, "normal"],
  ["Cinzel", "Cinzel-Medium.ttf", 500, "normal"],
  ["Cinzel", "Cinzel-SemiBold.ttf", 600, "normal"],
  ["Italiana", "Italiana-Regular.ttf", 400, "normal"],
]
  .map(([fam, file, w, st]) => `@font-face{font-family:'${fam}';src:url('${fileUrl(path.join(FONTS, file))}') format('truetype');font-weight:${w};font-style:${st};}`)
  .join("\n");

// Transition elements: what to keep when rendering a variant.
const VARIANTS = {
  "03.03": { matte: { css: ".tA{display:none!important}.tB{background:#fff!important}.tB *{visibility:hidden!important}.t-moon{background:#000!important}", opaque: true, label: "moonrise-matte" } },
  "03.04": {
    edge: { css: ".tA,.tB{display:none!important}", opaque: false, label: "gold-edge" },
    matte: { css: ".tA{display:none!important}.tB{background:#fff!important}.tB *{visibility:hidden!important}.wipe-edge{display:none!important}.t-wipe{background:#000!important}", opaque: true, label: "wipe-matte" },
  },
  "03.05": { leak: { css: ".tA,.tB{display:none!important}.t-leakT{background:#000!important}", opaque: true, label: "light-leak-screen" } },
};
const NATIVE_TRANSITIONS = new Set(["03.01", "03.02", "03.06", "03.07", "03.08"]);
// Components whose only text is fixed brand text (or text we blank out) are pre-rendered once.
const FIXED = { "06.02": {}, "06.03": {}, "02.03": { "the first look": "" } };

async function openKit(pw) {
  const browser = await pw.chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  // Use the bundled font files, never the network, so every machine renders identically.
  await page.route(/fonts\.(googleapis|gstatic)\.com/, (r) => r.abort());
  await page.goto(fileUrl(KIT_HTML), { waitUntil: "load" });
  await page.addStyleTag({ content: FONT_CSS });
  await page.evaluate(() => document.fonts.ready);
  return { browser, page };
}

async function catalog(page) {
  return page.evaluate(() =>
    [...document.querySelectorAll(".frame[data-code]")].map((f) => {
      const c = f.querySelector(".canvas");
      const texts = [];
      const w = document.createTreeWalker(c, NodeFilter.SHOW_TEXT);
      while (w.nextNode()) {
        const t = w.currentNode.nodeValue.replace(/\s+/g, " ").trim();
        if (t && !w.currentNode.parentElement.closest(".placeholder") && !texts.includes(t)) texts.push(t);
      }
      return {
        code: f.dataset.code,
        name: f.dataset.name,
        vertical: f.classList.contains("v"),
        texts,
        hasPlaceholder: !!c.querySelector(".placeholder"),
      };
    })
  );
}

function kindOf(item) {
  if (item.code.startsWith("03.")) return NATIVE_TRANSITIONS.has(item.code) ? "native-transition" : "transition-element";
  if (item.texts.length === 0 || FIXED[item.code]) return "prerender";
  return "text";
}

async function renderOne(page, code, opts) {
  const vertical = await page.evaluate((code) => document.querySelector(`.frame[data-code="${code}"]`)?.classList.contains("v"), code);
  if (vertical === undefined || vertical === null) throw new Error(`No kit component ${code}. Run "list".`);
  const W = vertical ? 1080 : 1920, H = vertical ? 1920 : 1080;
  await page.setViewportSize({ width: W, height: H });

  const variant = opts.variant ? (VARIANTS[code] || {})[opts.variant] : null;
  if (opts.variant && !variant) throw new Error(`Component ${code} has no "${opts.variant}" variant.`);

  // Isolate the component on a transparent 1:1 stage and start its animations.
  const info = await page.evaluate(
    ({ code, W, H, textMap, extraCss, opaque }) => {
      const src = document.querySelector(`.frame[data-code="${code}"] .canvas`);
      const canvas = src.cloneNode(true);
      // The kit keeps its <style> tags inside <body>, so hide the page instead of deleting it.
      document.documentElement.style.background = "transparent";
      const st = document.createElement("style");
      st.textContent = `html,body{margin:0!important;padding:0!important;background:transparent!important;overflow:hidden!important}
        .stage.frame{position:fixed!important;left:0;top:0;width:${W}px!important;height:${H}px!important;max-width:none!important;aspect-ratio:auto!important;border:0!important;background:transparent!important;cursor:default}
        .stage .canvas{transform:none!important;background:transparent}
        body>*:not(.stage):not(style):not(link):not(script){display:none!important}
        .stage .replay,.stage .dlbtn{display:none!important}
        .stage .placeholder{background:none!important;color:transparent!important}
        .stage .placeholder *{visibility:hidden!important}
        ${extraCss || ""}`;
      document.head.appendChild(st);
      const stage = document.createElement("div");
      stage.className = "frame stage";
      stage.appendChild(canvas);
      document.body.appendChild(stage);

      // Footage slots become transparent; if a slot fills the frame, so does everything behind it.
      if (!opaque) {
        const cr = { w: W, h: H };
        canvas.querySelectorAll(".placeholder").forEach((ph) => {
          const r = ph.getBoundingClientRect();
          if (r.width >= cr.w - 2 && r.height >= cr.h - 2) {
            let el = ph.parentElement;
            while (el && el !== stage) { el.style.setProperty("background", "transparent", "important"); el = el.parentElement; }
          }
        });
      }

      // Replace sample copy with the job's text.
      const missing = [];
      for (const [from, to] of Object.entries(textMap || {})) {
        let hit = false;
        const w = document.createTreeWalker(canvas, NodeFilter.SHOW_TEXT);
        while (w.nextNode()) {
          const n = w.currentNode;
          const norm = n.nodeValue.replace(/\s+/g, " ");
          if (norm.includes(from)) { n.nodeValue = norm.split(from).join(to); hit = true; }
        }
        canvas.querySelectorAll(".count[data-to]").forEach((el) => { if (el.dataset.to === from) { el.dataset.to = to; hit = true; } });
        if (!hit) missing.push(from);
      }

      stage.classList.add("play");
      const anims = document.getAnimations();
      let end = 0;
      for (const a of anims) {
        a.pause();
        const t = a.effect.getTiming();
        if (t.iterations !== Infinity) end = Math.max(end, (t.delay || 0) + (Number(t.duration) || 0) * (t.iterations || 1) + (t.endDelay || 0));
      }
      if (canvas.querySelector(".count")) end = Math.max(end, 1400);
      return { end, missing, count: anims.length };
    },
    { code, W, H, textMap: opts.text || {}, extraCss: variant ? variant.css : "", opaque: variant ? variant.opaque : false }
  );
  if (info.missing.length) console.warn(`Warning: text not found in ${code}: ${info.missing.map((s) => JSON.stringify(s)).join(", ")} (run "texts ${code}")`);
  await page.evaluate(() => document.fonts.ready);

  const durS = Math.max(3, info.end / 1000 + (opts.hold ?? 2));
  const frames = Math.round((durS * FPS_NUM) / FPS_DEN);
  const out = opts.out;
  fs.mkdirSync(path.dirname(path.resolve(out)), { recursive: true });

  const ff = spawn("ffmpeg", [
    "-hide_banner", "-loglevel", "error", "-y",
    "-f", "image2pipe", "-framerate", `${FPS_NUM}/${FPS_DEN}`, "-i", "-",
    "-c:v", "prores_ks", "-profile:v", "4", "-pix_fmt", "yuva444p10le", "-vendor", "apl0",
    "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
    "-metadata", `comment=Buwan Films kit ${code}`, out,
  ], { stdio: ["pipe", "inherit", "inherit"] });
  const ffDone = new Promise((res, rej) => { ff.on("error", rej); ff.on("exit", (c) => (c === 0 ? res() : rej(new Error(`ffmpeg exited ${c}`)))); });

  let last;
  for (let i = 0; i < frames; i++) {
    const ms = (i * 1000 * FPS_DEN) / FPS_NUM;
    await page.evaluate((ms) => {
      for (const a of document.getAnimations()) a.currentTime = ms;
      document.querySelectorAll(".count[data-to]").forEach((el) => {
        const p = Math.min(1, ms / 1400), e = 1 - Math.pow(1 - p, 3);
        el.textContent = Math.round(parseFloat(el.dataset.to) * e);
      });
    }, ms);
    last = await page.screenshot({ omitBackground: true, type: "png" });
    if (!ff.stdin.write(last)) await new Promise((r) => ff.stdin.once("drain", r));
  }
  ff.stdin.end();
  await ffDone;
  if (opts.still) fs.writeFileSync(out.replace(/\.mov$/i, ".png"), last);
  return { out, seconds: +durS.toFixed(2), frames, size: `${W}x${H}` };
}

function parseArgs(argv) {
  const o = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--still" || a === "--json") o[a.slice(2)] = true;
    else if (a.startsWith("--")) o[a.slice(2)] = argv[++i];
    else o._.push(a);
  }
  if (o.hold !== undefined) o.hold = parseFloat(o.hold);
  if (o.text) {
    const t = fs.existsSync(o.text) ? fs.readFileSync(o.text, "utf8") : o.text;
    o.text = JSON.parse(t);
  }
  return o;
}

(async () => {
  const args = parseArgs(process.argv.slice(2));
  const [cmd, arg] = args._;
  if (!cmd || !["list", "texts", "render", "prerender"].includes(cmd)) {
    console.log(fs.readFileSync(__filename, "utf8").split("\n").slice(1, 18).map((l) => l.replace(/^\/\/ ?/, "")).join("\n"));
    process.exit(cmd ? 1 : 0);
  }
  const pw = loadPlaywright();
  const { browser, page } = await openKit(pw);
  try {
    const items = await catalog(page);
    if (cmd === "list") {
      if (args.json) console.log(JSON.stringify(items.map((i) => ({ ...i, kind: kindOf(i) })), null, 1));
      else for (const i of items) console.log(`${i.code}  ${i.name.padEnd(26)} ${i.vertical ? "1080x1920" : "1920x1080"}  ${kindOf(i).padEnd(18)} ${i.texts.length ? i.texts.length + " text" : ""}`);
    } else if (cmd === "texts") {
      const i = items.find((x) => x.code === arg);
      if (!i) throw new Error(`No component ${arg}`);
      console.log(JSON.stringify(Object.fromEntries(i.texts.map((t) => [t, t])), null, 2));
    } else if (cmd === "render") {
      const i = items.find((x) => x.code === arg);
      if (!i) throw new Error(`No component ${arg}`);
      const label = args.variant ? (VARIANTS[arg] || {})[args.variant]?.label || args.variant : slug(i.name);
      const out = args.out || `${arg}_${label}.mov`;
      const r = await renderOne(page, arg, { ...args, out });
      console.log(`Rendered ${r.out}  ${r.size}  ${r.seconds}s  ${r.frames} frames  ProRes 4444 + alpha, 23.976`);
    } else if (cmd === "prerender") {
      const dir = arg || "kit-clips";
      const jobs = [];
      for (const i of items) {
        const k = kindOf(i);
        const sec = i.code.startsWith("08.") ? "corporate" : "wedding";
        if (k === "prerender") jobs.push({ code: i.code, text: FIXED[i.code] || {}, out: path.join(dir, sec, `${i.code}_${slug(i.name)}.mov`) });
        if (k === "transition-element")
          for (const [v, def] of Object.entries(VARIANTS[i.code])) jobs.push({ code: i.code, variant: v, out: path.join(dir, "transitions", `${i.code}_${def.label}.mov`) });
      }
      for (const j of jobs) {
        const r = await renderOne(page, j.code, { variant: j.variant, text: j.text, out: j.out, hold: args.hold, still: true });
        console.log(`${r.out}  ${r.seconds}s`);
        await page.goto(fileUrl(KIT_HTML), { waitUntil: "load" });
        await page.addStyleTag({ content: FONT_CSS });
      }
    }
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e.message || e);
  process.exit(1);
});
