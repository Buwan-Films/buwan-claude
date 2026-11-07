#!/usr/bin/env node
// Starts the pinned Premiere Pro MCP server on Windows and macOS.
// Windows needs npx.cmd through a shell; macOS runs npx directly.
// Change PINNED only together with the MCP Bridge panel in Premiere (npx -y premiere-pro-mcp@<version> --install-cep).
const { spawn } = require("child_process");

const PINNED = "premiere-pro-mcp@1.11.5";
const isWin = process.platform === "win32";

const child = spawn(isWin ? "npx.cmd" : "npx", ["-y", PINNED], {
  stdio: "inherit",
  shell: isWin,
  // Buwan steps (import/organize/build) run long inside Premiere; give the bridge 2 minutes before it gives up
  env: { PREMIERE_TIMEOUT_MS: "120000", ...process.env },
});

child.on("error", (err) => {
  process.stderr.write(`buwan-premiere: could not start ${PINNED}: ${err.message}\nIs Node.js 20.19+ installed and on PATH?\n`);
  process.exit(1);
});
child.on("exit", (code, signal) => process.exit(code ?? (signal ? 1 : 0)));
for (const sig of ["SIGINT", "SIGTERM"]) process.on(sig, () => child.kill(sig));
