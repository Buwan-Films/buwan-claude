#!/usr/bin/env node
// Prints the exact ExtendScript to pass to the bridge's execute_extendscript tool.
//   node premiere-snippet.js <step> <manifest.json> [opts-object-literal]
//   node premiere-snippet.js organize "D:\Buwan\projects\2026-11-15_Santos-Reyes\edit\premiere\manifest.json" "{limit:200}"
// Steps: status import organize cull grade enhance deadair aroll sync build all
const path = require("path");
const fs = require("fs");

const [step, manifest, opts] = process.argv.slice(2);
const steps = ["status", "import", "organize", "cull", "grade", "enhance", "deadair", "aroll", "sync", "build", "all"];
if (!step || !manifest || !steps.includes(step)) {
  console.error(`usage: premiere-snippet.js <${steps.join("|")}> <manifest.json> [opts]`);
  process.exit(2);
}
const jsx = path.resolve(__dirname, "..", "jsx", "buwan.jsx");
if (!fs.existsSync(jsx)) { console.error("buwan.jsx not found at " + jsx); process.exit(2); }
const mf = path.resolve(manifest);
if (!fs.existsSync(mf)) { console.error("manifest not found: " + mf + "  (run: node <buwan>/scripts/assemble.js premiere <project>)"); process.exit(2); }
// ExtendScript File() takes forward slashes on both platforms; escape for a JS string literal
const esc = (p) => p.replace(/\\/g, "/").replace(/"/g, '\\"');
const optLit = opts ? opts.replace(/"/g, '\\"') : "";
const timeouts = { status: 60000, import: 600000, organize: 600000, cull: 120000, grade: 300000, enhance: 300000, deadair: 600000, aroll: 300000, sync: 300000, build: 600000, all: 1800000 };
const code = `$.evalFile(new File("${esc(jsx)}")); return __result(BUWAN.run("${step}", "${esc(mf)}"${optLit ? `, "${optLit}"` : ""}));`;
console.log(`execute_extendscript  (timeout_ms: ${timeouts[step]})\n\n${code}\n`);
