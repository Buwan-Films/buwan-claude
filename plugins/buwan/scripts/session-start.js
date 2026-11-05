#!/usr/bin/env node
// SessionStart: put the Buwan rule card in context at the start of every session,
// so editors don't have to remember to load the house rules.
const fs = require("fs");
const path = require("path");

const root = process.env.CLAUDE_PLUGIN_ROOT || path.join(__dirname, "..");
let version = "unknown";
try {
  version = JSON.parse(fs.readFileSync(path.join(root, ".claude-plugin", "plugin.json"), "utf8")).version;
} catch {}

const nle = (process.env.CLAUDE_PLUGIN_OPTION_NLE || "premiere").toLowerCase();
const editor = process.env.CLAUDE_PLUGIN_OPTION_EDITOR_NAME || "(not set)";
const playbook = { premiere: "/buwan:premiere", "final-cut": "/buwan:final-cut", resolve: "/buwan:resolve" }[nle] || "/buwan:premiere";

let cwd = process.cwd();
try {
  const input = JSON.parse(fs.readFileSync(0, "utf8") || "{}");
  if (input.cwd) cwd = input.cwd;
} catch {}
const isWorkspace = ["projects", "kit"].every((d) => fs.existsSync(path.join(cwd, d)));

const card = `Buwan Films plugin v${version} is active. Editor: ${editor}. Editing app: ${nle} (playbook ${playbook}).
These studio rules apply to every editing task in this session:
- Load /buwan:house-rules before any edit work, and ${playbook} for app steps. They define brand, beats, Story-Lock, pacing, audio specs and deliverables.
- Determine shoot type first: wedding or corporate.
- sources/ folders are read-only. Writes, moves and deletes there are blocked by a hook.
- Workflow skills: /buwan:intake -> /buwan:assemble (cull, music, multicam sync) -> /buwan:organize -> /buwan:plot -> /buwan:rough-cut -> /buwan:proof-gate -> /buwan:audio -> /buwan:grade -> /buwan:graphics -> /buwan:sfx -> /buwan:review -> /buwan:export -> /buwan:clipper. /buwan:sde = same-day mode. /buwan:check and /buwan:setup-kit for setup.
- Clip colors, bins, LUTs and kit graphics are shared studio standards (see house rules). Use them exactly.
- Never hand-write FCPXML: organize/selects/timelines come from the assemble engine (node scripts/assemble.js), which validates against Apple's DTD.
- Graphics come from the Buwan Video Component Kit only; never invent off-brand graphics.
- Keep vows and speeches verbatim (Taglish). Flag proper nouns before captions ship.${isWorkspace ? "" : `
- Note: ${cwd} is not a Buwan workspace (no projects/ and kit/ folders). If this is editing work, ask the editor to start Claude in their Buwan workspace folder.`}`;

process.stdout.write(JSON.stringify({ hookSpecificOutput: { hookEventName: "SessionStart", additionalContext: card } }));
