#!/usr/bin/env node
// PreToolUse: keep every sources/ folder read-only.
// - File tools (Write/Edit/MultiEdit/NotebookEdit) may not target anything inside a sources/, RAW_COPY/, BY_CATEGORY/ or listed original folder.
// - Shell commands may READ from sources/ and COPY into it (intake), but may not delete, move,
//   rename, overwrite, redirect into, mirror-sync, or unlock it.
// Exit 2 blocks the tool call; stderr is shown to Claude as the reason.
const fs = require("fs");
const path = require("path");
const os = require("os");

let input = {};
try {
  input = JSON.parse(fs.readFileSync(0, "utf8") || "{}");
} catch {
  process.exit(0);
}
const tool = input.tool_name || "";
const ti = input.tool_input || {};

// Protected: any sources/ folder, any RAW_COPY/ folder (the working copy on the drive), any BY_CATEGORY/ folder
// (the same copy organized by category, cloned by `assemble.js bycategory`), and every
// path listed in ~/.buwan/protected-paths.txt (the original card folders, written by `assemble.js workcopy`).
let protectedRoots = [];
try {
  protectedRoots = fs.readFileSync(path.join(os.homedir(), ".buwan", "protected-paths.txt"), "utf8")
    .split(/\r?\n/).map((l) => l.trim()).filter(Boolean).map((l) => l.replace(/[\\/]+$/, "").toLowerCase());
} catch {}
const SRC_RE = /(^|[\\/])(sources|RAW_COPY|BY_CATEGORY)([\\/]|$)/i;
const escapeRe = (x) => x.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const SRC = {
  test(str) {
    if (SRC_RE.test(str)) return true;
    const low = String(str).replace(/\\/g, "/").toLowerCase();
    // a protected root matches itself and anything under it — not a sibling like <root>_WORK/
    return protectedRoots.some((r) => new RegExp(escapeRe(r.replace(/\\/g, "/")) + "(/|$|[\\s\"'])").test(low));
  },
};
const block = (why) => {
  process.stderr.write(
    `Blocked by Buwan Films source protection: ${why}\n` +
      `sources/, RAW_COPY/, BY_CATEGORY/ and the original card folders hold footage and are read-only. Write outputs to edit/, PROJECT/, AUDIO_CLEAN/, captions/ or exports/ instead. ` +
      `If the editor truly needs to change originals, they must do it themselves outside Claude.`
  );
  process.exit(2);
};

if (["Write", "Edit", "MultiEdit", "NotebookEdit"].includes(tool)) {
  const p = ti.file_path || ti.notebook_path || "";
  if (SRC.test(p)) block(`${tool} on ${p}`);
  process.exit(0);
}

if (tool === "Bash" || tool === "PowerShell") {
  const cmd = String(ti.command || "");
  if (!SRC.test(cmd)) process.exit(0);

  // Split into simple commands so "cp a sources/x && rm b" is judged per part.
  const parts = cmd.split(/&&|\|\||;|\r?\n|\|(?!\|)/);
  for (const raw of parts) {
    const part = raw.trim();
    if (!SRC.test(part)) continue;

    const destructive =
      /(^|\s|\(|&)(rm|rmdir|unlink|shred|truncate|del|erase|rd|mv|move|ren|rename|Remove-Item|ri|Move-Item|mi|Rename-Item|rni|Clear-Content|Set-Content|sc|Add-Content|ac|Out-File|Set-ItemProperty|chown|icacls|takeown)(\s|$)/i;
    if (destructive.test(part)) block(`shell command changes sources/: ${part}`);

    // Unlocking: attrib -R, chmod that adds write. (attrib +R / chmod a-w are the intake lock and are allowed.)
    if (/\battrib\b/i.test(part) && /(^|\s)-R(\s|$)/.test(part)) block(`removing read-only from sources/: ${part}`);
    if (/\bchmod\b/i.test(part) && /(\+w|=\w*w|\b[0-7]?[2367][0-7]{2}\b)/.test(part)) block(`making sources/ writable: ${part}`);
    if (/\bCopy-Item\b/i.test(part) && /-Force\b/i.test(part)) block(`Copy-Item -Force can overwrite originals in sources/: ${part}`);

    // Redirection into sources/
    if (/>{1,2}\s*["']?[^\s"']*[\\/]?sources([\\/]|\b)/i.test(part)) block(`redirect into sources/: ${part}`);

    // Mirror/purge syncs can delete originals
    if (/\brobocopy\b/i.test(part) && /\/(MIR|PURGE|MOV|MOVE)\b/i.test(part)) block(`robocopy /MIR, /PURGE or /MOVE touching sources/: ${part}`);
    if (/\brsync\b/i.test(part) && /--(delete|remove-source-files)/i.test(part)) block(`rsync delete option touching sources/: ${part}`);

    // ffmpeg / sox / other writers whose OUTPUT (last argument) lands in sources/
    if (/\b(ffmpeg|sox|magick|convert|HandBrakeCLI)\b/i.test(part)) {
      const tokens = part.match(/"[^"]*"|'[^']*'|\S+/g) || [];
      const last = (tokens[tokens.length - 1] || "").replace(/^["']|["']$/g, "");
      if (SRC.test(last)) block(`render output into sources/: ${part}`);
    }
  }
}
process.exit(0);
