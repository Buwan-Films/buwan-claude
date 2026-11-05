#!/usr/bin/env node
// Buwan kit setup — run once per computer (and again after kit updates).
//   node setup-kit.js --workspace <Buwan workspace folder> [--deps <folder>] [--skip-render] [--skip-fonts]
// 1. Installs the brand fonts for the current user (Windows, macOS, Linux).
// 2. Copies logo, fonts, LUTs and grade targets into <workspace>/kit/.
// 3. Installs the renderer (Playwright + Chromium) into the deps folder.
// 4. Renders the reusable kit clips into <workspace>/kit/ (wedding/, transitions/).
const fs = require("fs");
const os = require("os");
const path = require("path");
const { execFileSync, spawnSync } = require("child_process");

const ROOT = path.join(__dirname, "..");
const KIT = path.join(ROOT, "kit");
const PLAYWRIGHT_VERSION = "1.63.0";

const args = process.argv.slice(2);
const opt = (n, d) => { const i = args.indexOf(`--${n}`); return i >= 0 ? args[i + 1] : d; };
const flag = (n) => args.includes(`--${n}`);
const ws = path.resolve(opt("workspace", process.cwd()));
const deps = path.resolve(opt("deps", path.join(os.homedir(), ".buwan", "deps")));
const isWin = process.platform === "win32", isMac = process.platform === "darwin";
const report = [];
const ok = (step, detail) => report.push(["PASS", step, detail || ""]);
const bad = (step, detail) => report.push(["FAIL", step, detail || ""]);
const has = (cmd, a = ["-version"]) => spawnSync(cmd, a, { stdio: "ignore", shell: isWin }).status === 0;

function copyDir(src, dst) {
  fs.mkdirSync(dst, { recursive: true });
  let n = 0;
  for (const e of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, e.name), d = path.join(dst, e.name);
    if (e.isDirectory()) n += copyDir(s, d);
    else { fs.copyFileSync(s, d); n++; }
  }
  return n;
}

// 1. Fonts
if (!flag("skip-fonts")) {
  const fonts = fs.readdirSync(path.join(KIT, "fonts")).filter((f) => /\.ttf$/i.test(f));
  try {
    if (isWin) {
      const dir = path.join(process.env.LOCALAPPDATA, "Microsoft", "Windows", "Fonts");
      fs.mkdirSync(dir, { recursive: true });
      for (const f of fonts) {
        const dst = path.join(dir, f);
        try { fs.copyFileSync(path.join(KIT, "fonts", f), dst); } catch (e) { if (e.code !== "EBUSY" && e.code !== "EPERM") throw e; }
        const name = f.replace(/\.ttf$/i, "").replace(/([a-z])([A-Z])/g, "$1 $2").replace(/-/g, " ") + " (TrueType)";
        execFileSync("reg", ["add", "HKCU\\Software\\Microsoft\\Windows NT\\CurrentVersion\\Fonts", "/v", name, "/t", "REG_SZ", "/d", dst, "/f"], { stdio: "ignore" });
      }
    } else {
      const dir = isMac ? path.join(os.homedir(), "Library", "Fonts") : path.join(os.homedir(), ".local", "share", "fonts");
      fs.mkdirSync(dir, { recursive: true });
      for (const f of fonts) fs.copyFileSync(path.join(KIT, "fonts", f), path.join(dir, f));
      if (!isMac) spawnSync("fc-cache", ["-f"], { stdio: "ignore" });
    }
    ok("Fonts installed for this user", `${fonts.length} files (Cormorant Garamond, Cinzel, Italiana). Restart your editing app to see them.`);
  } catch (e) {
    bad("Fonts", e.message);
  }
}

// 2. Kit resources into the workspace
try {
  let n = 0;
  for (const d of ["logo", "fonts", "luts", "grade"]) if (fs.existsSync(path.join(KIT, d))) n += copyDir(path.join(KIT, d), path.join(ws, "kit", d));
  for (const d of ["wedding", "corporate", "transitions", "overlays"]) fs.mkdirSync(path.join(ws, "kit", d), { recursive: true });
  ok("Kit files copied", `${n} files into ${path.join(ws, "kit")}`);
} catch (e) {
  bad("Kit files", e.message);
}

// 3 + 4. Renderer and pre-rendered clips
if (!has("ffmpeg")) bad("ffmpeg", isWin ? "Install: winget install Gyan.FFmpeg  (then reopen the terminal)" : "Install: brew install ffmpeg");
else ok("ffmpeg found");

if (!flag("skip-render")) {
  const pwDir = path.join(deps, "node_modules", "playwright");
  if (!fs.existsSync(pwDir)) {
    fs.mkdirSync(deps, { recursive: true });
    const r = spawnSync(isWin ? "npm.cmd" : "npm", ["install", "--prefix", deps, `playwright@${PLAYWRIGHT_VERSION}`, "--no-audit", "--no-fund"], { stdio: "inherit", shell: isWin });
    if (r.status !== 0) bad("Playwright install", "npm install failed");
  }
  if (fs.existsSync(pwDir)) {
    const r = spawnSync(process.execPath, [path.join(pwDir, "cli.js"), "install", "chromium"], { stdio: "inherit" });
    if (r.status === 0) ok("Renderer installed", `Playwright ${PLAYWRIGHT_VERSION} + Chromium in ${deps}`);
    else bad("Chromium install", "playwright install chromium failed");
  }
  if (report.every((x) => x[0] !== "FAIL")) {
    const r = spawnSync(process.execPath, [path.join(__dirname, "render-kit.js"), "prerender", path.join(ws, "kit")], {
      stdio: "inherit",
      env: { ...process.env, BUWAN_DEPS: deps },
    });
    if (r.status === 0) ok("Reusable kit clips rendered", "logo, logo reveal, logo placement, watermark, letterbox, placeholders, moonrise matte, gold wipe edge + matte, light leak");
    else bad("Kit clip render", "see errors above");
  }
}

// 5. Python environment for the assemble engine (cull, music analysis, multicam sync, FCPXML builder)
if (!flag("skip-python")) {
  const venv = path.join(os.homedir(), ".buwan", "venv");
  const py = isWin ? path.join(venv, "Scripts", "python.exe") : path.join(venv, "bin", "python");
  const sysPy = ["python3", "python"].find((p) => spawnSync(p, ["-c", "import sys; assert sys.version_info >= (3, 9)"], { stdio: "ignore", shell: isWin }).status === 0);
  if (!sysPy) bad("Python 3.9+", isMac ? "Install: brew install python" : isWin ? "Install: winget install Python.Python.3.12" : "Install python3");
  else {
    if (!fs.existsSync(py)) spawnSync(sysPy, ["-m", "venv", venv], { stdio: "inherit", shell: isWin });
    const r = spawnSync(py, ["-m", "pip", "install", "-q", "--upgrade", "pip", "-r", path.join(ROOT, "assemble", "requirements.txt")], { stdio: "inherit" });
    if (r.status === 0) ok("Assemble engine (Python)", `numpy, scipy, librosa, soundfile, pillow in ${venv}`);
    else bad("Assemble engine (Python)", "pip install failed — see errors above");
  }
  // FCPXML DTD for validation (Apple's DTD, mirrored in the CommandPost project)
  const dtdDir = path.join(os.homedir(), ".buwan", "dtd");
  const dtd = path.join(dtdDir, "FCPXMLv1_11.dtd");
  if (!fs.existsSync(dtd)) {
    fs.mkdirSync(dtdDir, { recursive: true });
    const url = "https://raw.githubusercontent.com/CommandPost/CommandPost/develop/src/extensions/cp/apple/fcpxml/dtd/FCPXMLv1_11.dtd";
    const r = spawnSync("curl", ["-fsSL", "-o", dtd, url], { stdio: "ignore", shell: isWin });
    if (r.status === 0) ok("FCPXML DTD", "downloaded for validation"); else report.push(["INFO", "FCPXML DTD", "not downloaded (validation will be skipped)"]);
  } else ok("FCPXML DTD", "present");
}

console.log("\nBUWAN KIT SETUP");
for (const [v, s, d] of report) console.log(`${v.padEnd(5)} ${s.padEnd(30)} ${d}`);
process.exit(report.some((x) => x[0] === "FAIL") ? 1 : 0);
