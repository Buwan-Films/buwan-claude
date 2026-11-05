#!/usr/bin/env node
// Runs the Buwan assemble engine with the Python environment that /buwan:setup-kit created.
//   node assemble.js <assemble.py arguments...>
const { spawnSync } = require("child_process");
const path = require("path");
const os = require("os");
const fs = require("fs");
const venv = process.env.BUWAN_VENV || path.join(os.homedir(), ".buwan", "venv");
const py = process.platform === "win32" ? path.join(venv, "Scripts", "python.exe") : path.join(venv, "bin", "python");
if (!fs.existsSync(py)) {
  console.error(`Buwan assemble: Python environment not found at ${venv}. Run /buwan:setup-kit first.`);
  process.exit(3);
}
const r = spawnSync(py, [path.join(__dirname, "..", "assemble", "assemble.py"), ...process.argv.slice(2)], { stdio: "inherit", env: { ...process.env, BUWAN_FCPXML_DTD: process.env.BUWAN_FCPXML_DTD || path.join(os.homedir(), ".buwan", "dtd", "FCPXMLv1_11.dtd") } });
process.exit(r.status ?? 1);
