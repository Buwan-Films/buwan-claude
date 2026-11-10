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
- sources/ folders, RAW_COPY/ and BY_CATEGORY/ folders and the original card folders are read-only. Writes, moves and deletes there are blocked by a hook. The basics read the raw folder and write new enhanced clips next to it (<raw>_ENHANCED_<date-time>/); speech moments go to <raw>_SPEECH_<date-time>/.
- New wedding project = /buwan:basics only: new enhanced clips into <raw>_ENHANCED_<date-time>/ (exposure and white balance fixed on every clip, shaky Creative/Glider best cut + smooth glide, NO grade); no copying, no dedupe, no file organizing, no speech work. The editor made the project and placed the music. Stop there. New cards during the day: /buwan:sync (only the new clips, into the same _ENHANCED_ folder). On request only: /buwan:multicam (interviews/vows/speeches: the editor gives the clip names of one moment -> angles synced on the best clean audio, dead air out, <raw>_SPEECH_<date-time>/INTERVIEWS|VOWS|SPEECHES/), /buwan:grade (the look, applied in the app), /buwan:plot (story), /buwan:rough-cut / build (cut), then /buwan:proof-gate -> /buwan:audio -> /buwan:grade -> /buwan:graphics -> /buwan:sfx -> /buwan:review -> /buwan:export -> /buwan:clipper. /buwan:sde = the full same-day flow when asked. /buwan:check and /buwan:setup-kit for setup.
- Clip colors, bins, LUTs and kit graphics are shared studio standards (see house rules). Use them exactly.
- Never hand-write FCPXML: organize/selects/timelines come from the assemble engine (node scripts/assemble.js), which validates against Apple's DTD.${nle === "premiere" ? "\n- Premiere: apply the engine's decisions in the open project with /buwan-premiere:premiere-apply (bins, label colors, cull, dead-air subclips, A-Roll clean, SYNC, the SDE Cut, LUT, dialogue levels) — never redo these by hand. Wedding day: /buwan-premiere:wedding-day = the basics in the open project (bridge step basics), then stop." : ""}
- Graphics come from the Buwan Video Component Kit only; never invent off-brand graphics.
- Keep vows and speeches verbatim (Taglish). Flag proper nouns before captions ship.${isWorkspace ? "" : `
- Note: ${cwd} is not a Buwan workspace (no projects/ and kit/ folders). If this is editing work, ask the editor to start Claude in their Buwan workspace folder.`}`;

process.stdout.write(JSON.stringify({ hookSpecificOutput: { hookEventName: "SessionStart", additionalContext: card } }));
