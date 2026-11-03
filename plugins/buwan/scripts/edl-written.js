#!/usr/bin/env node
// PostToolUse: whenever Claude writes an .edl, measure it right away and put the
// numbers in front of Claude, so the proof gate is never skipped.
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

let input = {};
try {
  input = JSON.parse(fs.readFileSync(0, "utf8") || "{}");
} catch {
  process.exit(0);
}
const file = (input.tool_input || {}).file_path || "";
if (!/\.edl$/i.test(file) || !fs.existsSync(file)) process.exit(0);

const type = /_corporate([\\/]|$)/i.test(file) ? "corporate" : "wedding";
const mode = /select|speech|story/i.test(path.basename(file)) ? "speech" : "cut";
let report;
try {
  report = execFileSync(process.execPath, [path.join(__dirname, "proof-gate.js"), file, "--type", type, "--mode", mode], {
    encoding: "utf8",
  });
} catch (e) {
  report = (e.stdout || "") + (e.stderr || "");
}
process.stdout.write(
  JSON.stringify({
    hookSpecificOutput: {
      hookEventName: "PostToolUse",
      additionalContext: `Buwan proof gate ran automatically on ${path.basename(file)} (${type}, ${mode} mode). Report these results to the editor and fix FAILs before moving on:\n${report}`,
    },
  })
);
