from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import threading
import time
import webbrowser
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from ..commands import PORTED_COMMANDS, find_commands
from ..port_manifest import build_port_manifest
from ..runtime import PortRuntime
from ..tools import PORTED_TOOLS, find_tools

REPO_ROOT = Path(__file__).resolve().parents[2]
RUST_ROOT = REPO_ROOT / "rust"
DEFAULT_CLAW_MODEL = "sonnet"
DEFAULT_CLAW_PERMISSION_MODE = "read-only"
CLAW_TIMEOUT_SECONDS = 90


HTML_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Claw Code Control Room</title>
  <style>
    :root {
      --bg: #f5efe2;
      --panel: rgba(255, 250, 240, 0.92);
      --ink: #1a1611;
      --muted: #6e6356;
      --accent: #cd5c2b;
      --accent-strong: #a53e1f;
      --line: rgba(26, 22, 17, 0.12);
      --shadow: 0 20px 60px rgba(78, 48, 20, 0.16);
      --code: #efe2c7;
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Georgia, "Iowan Old Style", "Palatino Linotype", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(205, 92, 43, 0.18), transparent 30%),
        radial-gradient(circle at top right, rgba(63, 114, 87, 0.16), transparent 26%),
        linear-gradient(180deg, #f9f3e8 0%, var(--bg) 55%, #efe6d4 100%);
      min-height: 100vh;
    }

    .shell {
      width: min(1220px, calc(100vw - 32px));
      margin: 24px auto 40px;
      display: grid;
      grid-template-columns: 320px 1fr;
      gap: 20px;
    }

    .card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(10px);
    }

    .sidebar {
      padding: 24px;
      position: sticky;
      top: 20px;
      align-self: start;
    }

    .eyebrow {
      text-transform: uppercase;
      letter-spacing: 0.18em;
      color: var(--accent-strong);
      font-size: 12px;
      margin-bottom: 10px;
    }

    h1, h2, h3 {
      margin: 0;
      font-weight: 600;
    }

    h1 {
      font-size: clamp(34px, 4.8vw, 58px);
      line-height: 0.96;
      margin-bottom: 16px;
    }

    .lede, .muted {
      color: var(--muted);
    }

    .stats {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-top: 24px;
    }

    .stat {
      background: rgba(255,255,255,0.58);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px;
    }

    .stat strong {
      display: block;
      font-size: 26px;
      margin-bottom: 4px;
    }

    .stack {
      display: grid;
      gap: 20px;
    }

    .hero {
      padding: 28px;
      overflow: hidden;
      position: relative;
    }

    .hero::after {
      content: "";
      position: absolute;
      inset: auto -10% -25% auto;
      width: 280px;
      height: 280px;
      background: radial-gradient(circle, rgba(205, 92, 43, 0.2), transparent 60%);
      pointer-events: none;
    }

    .hero-grid {
      display: grid;
      grid-template-columns: 1.1fr 0.9fr;
      gap: 20px;
    }

    .hero-panel {
      background: rgba(255,255,255,0.62);
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 18px;
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 20px;
    }

    .section {
      padding: 22px;
    }

    .toolbar {
      display: flex;
      gap: 12px;
      margin-top: 16px;
      flex-wrap: wrap;
    }

    input, textarea, button {
      font: inherit;
    }

    input, textarea {
      width: 100%;
      border: 1px solid rgba(26, 22, 17, 0.16);
      background: rgba(255,255,255,0.76);
      border-radius: 16px;
      padding: 14px 16px;
      color: var(--ink);
    }

    textarea {
      min-height: 128px;
      resize: vertical;
    }

    button {
      border: 0;
      border-radius: 999px;
      background: var(--accent);
      color: white;
      padding: 12px 18px;
      cursor: pointer;
      transition: transform 140ms ease, background 140ms ease;
    }

    button.secondary {
      background: #244a3d;
    }

    button:hover {
      transform: translateY(-1px);
      background: var(--accent-strong);
    }

    .list {
      display: grid;
      gap: 12px;
      margin-top: 16px;
    }

    .item {
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px 16px;
      background: rgba(255,255,255,0.52);
    }

    .item small, .pill {
      color: var(--muted);
    }

    .pill {
      display: inline-block;
      margin-right: 8px;
      padding: 4px 10px;
      border-radius: 999px;
      background: rgba(26,22,17,0.06);
      font-size: 12px;
    }

    pre {
      background: var(--code);
      padding: 16px;
      border-radius: 18px;
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-word;
      border: 1px solid rgba(26, 22, 17, 0.08);
    }

    .empty {
      color: var(--muted);
      font-style: italic;
      padding: 10px 0 4px;
    }

    .status {
      margin-top: 14px;
      min-height: 22px;
      color: var(--muted);
    }

    @media (max-width: 980px) {
      .shell, .hero-grid, .grid {
        grid-template-columns: 1fr;
      }

      .sidebar {
        position: static;
      }
    }
  </style>
</head>
<body>
  <div class="shell">
    <aside class="card sidebar">
      <div class="eyebrow">Claw Code</div>
      <h1>Control<br>Room</h1>
      <p class="lede">A web surface for the Python porting workspace: browse mirrored commands and tools, route prompts, and preview runtime sessions from one place.</p>
      <div class="toolbar">
        <button onclick="window.location.href='/prompt'">Open Prompt Page</button>
      </div>
      <div class="stats" id="stats"></div>
      <div class="list" id="modules"></div>
    </aside>

    <main class="stack">
      <section class="card hero">
        <div class="hero-grid">
          <div>
            <div class="eyebrow">Workspace Pulse</div>
            <h2>Browse the agent surface before you drop into the terminal.</h2>
            <p class="muted">The UI stays thin on purpose: it fronts the existing Python routing/runtime helpers instead of reinventing them.</p>
            <div class="toolbar">
              <button id="refresh-overview">Refresh Overview</button>
              <button id="load-runtime" class="secondary">Preview Runtime Session</button>
            </div>
            <div class="status" id="overview-status"></div>
          </div>
          <div class="hero-panel">
            <div class="eyebrow">Session Preview</div>
            <pre id="runtime-preview">Press "Preview Runtime Session" to render a runtime bootstrap snapshot.</pre>
          </div>
        </div>
      </section>

      <section class="grid">
        <div class="card section">
          <div class="eyebrow">Command Atlas</div>
          <h3>Search mirrored commands</h3>
          <div class="toolbar">
            <input id="command-query" placeholder="Try: review, session, mcp">
            <button id="search-commands">Search</button>
          </div>
          <div class="list" id="commands"></div>
        </div>

        <div class="card section">
          <div class="eyebrow">Tool Atlas</div>
          <h3>Search mirrored tools</h3>
          <div class="toolbar">
            <input id="tool-query" placeholder="Try: MCP, Bash, read">
            <button id="search-tools">Search</button>
          </div>
          <div class="list" id="tools"></div>
        </div>
      </section>

      <section class="card section">
        <div class="eyebrow">Prompt Router</div>
        <h3>Route an actual prompt across the mirrored surface</h3>
        <textarea id="prompt-box" placeholder="Describe the task you want routed through the workspace.">review the MCP tool flow and summarize the likely path</textarea>
        <div class="toolbar">
          <button id="route-prompt">Route Prompt</button>
          <button id="bootstrap-prompt" class="secondary">Bootstrap Session</button>
        </div>
        <div class="grid" style="margin-top: 18px;">
          <div>
            <div class="eyebrow">Routed Matches</div>
            <div class="list" id="routes"></div>
          </div>
          <div>
            <div class="eyebrow">Bootstrap Output</div>
            <pre id="bootstrap-output">Bootstrap output will appear here.</pre>
          </div>
        </div>
      </section>

      <section class="card section">
        <div class="eyebrow">Live Claw</div>
        <h3>Run the real Rust `claw` binary</h3>
        <p class="muted">This uses the local Rust workspace directly and defaults to one-shot `read-only` execution so the browser can safely hit the real runtime.</p>
        <div class="toolbar">
          <input id="claw-model" value="sonnet" placeholder="model alias">
          <input id="claw-permission-mode" value="read-only" placeholder="permission mode">
          <button id="run-live-claw">Run Live Claw</button>
        </div>
        <div class="status" id="claw-status">Live runtime status loading...</div>
        <pre id="claw-output">Live `claw` output will appear here.</pre>
      </section>
    </main>
  </div>

  <script>
    async function fetchJson(url, options) {
      const response = await fetch(url, options);
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `Request failed: ${response.status}`);
      }
      return response.json();
    }

    function renderList(targetId, items, emptyText, formatter) {
      const target = document.getElementById(targetId);
      target.innerHTML = "";
      if (!items || items.length === 0) {
        target.innerHTML = `<div class="empty">${emptyText}</div>`;
        return;
      }
      for (const item of items) {
        const article = document.createElement("article");
        article.className = "item";
        article.innerHTML = formatter(item);
        target.appendChild(article);
      }
    }

    function setStatus(id, message) {
      document.getElementById(id).textContent = message;
    }

    async function loadOverview() {
      setStatus("overview-status", "Refreshing workspace overview...");
      const payload = await fetchJson("/api/overview");
      const stats = [
        ["Python files", payload.manifest.total_python_files],
        ["Commands", payload.commands.total],
        ["Tools", payload.tools.total],
        ["Modules", payload.manifest.top_level_modules.length],
      ];
      renderList("stats", stats, "", ([label, value]) => `<div class="stat"><strong>${value}</strong><span>${label}</span></div>`);
      renderList(
        "modules",
        payload.manifest.top_level_modules.slice(0, 8),
        "No modules found.",
        (module) => `<div class="item"><strong>${module.name}</strong><br><small>${module.file_count} files</small><div class="muted">${module.notes}</div></div>`
      );
      const claw = payload.claw_runtime;
      const availability = claw.available
        ? `Live claw ready via ${claw.strategy} at ${claw.command_path}`
        : `Live claw unavailable: ${claw.reason}`;
      document.getElementById("claw-status").textContent = availability;
      setStatus("overview-status", `Workspace root: ${payload.manifest.src_root}`);
    }

    async function searchCommands() {
      const query = document.getElementById("command-query").value.trim();
      const payload = await fetchJson(`/api/commands?q=${encodeURIComponent(query)}&limit=8`);
      renderList(
        "commands",
        payload.entries,
        "No command matches.",
        (entry) => `<strong>${entry.name}</strong><br><small>${entry.source_hint}</small><div class="muted">${entry.responsibility}</div>`
      );
    }

    async function searchTools() {
      const query = document.getElementById("tool-query").value.trim();
      const payload = await fetchJson(`/api/tools?q=${encodeURIComponent(query)}&limit=8`);
      renderList(
        "tools",
        payload.entries,
        "No tool matches.",
        (entry) => `<strong>${entry.name}</strong><br><small>${entry.source_hint}</small><div class="muted">${entry.responsibility}</div>`
      );
    }

    async function routePrompt() {
      const prompt = document.getElementById("prompt-box").value.trim();
      const payload = await fetchJson(`/api/route?prompt=${encodeURIComponent(prompt)}&limit=6`);
      renderList(
        "routes",
        payload.matches,
        "No routed matches.",
        (match) => `<span class="pill">${match.kind}</span><strong>${match.name}</strong><br><small>${match.source_hint}</small><div class="muted">score ${match.score}</div>`
      );
    }

    async function bootstrapPrompt() {
      const prompt = document.getElementById("prompt-box").value.trim();
      const payload = await fetchJson("/api/bootstrap", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, limit: 6 }),
      });
      document.getElementById("bootstrap-output").textContent = payload.markdown;
    }

    async function previewRuntime() {
      const payload = await fetchJson("/api/bootstrap", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: "review MCP tool flow", limit: 5 }),
      });
      document.getElementById("runtime-preview").textContent = payload.turn_output;
    }

    async function runLiveClaw() {
      const prompt = document.getElementById("prompt-box").value.trim();
      const model = document.getElementById("claw-model").value.trim() || "sonnet";
      const permissionMode = document.getElementById("claw-permission-mode").value.trim() || "read-only";
      document.getElementById("claw-status").textContent = "Running live claw prompt...";
      const payload = await fetchJson("/api/claw", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, model, permission_mode: permissionMode }),
      });
      document.getElementById("claw-status").textContent =
        payload.ok
          ? `Live claw completed via ${payload.runtime.strategy} in ${payload.duration_ms} ms`
          : `Live claw failed: ${payload.error || "unknown error"}`;
      document.getElementById("claw-output").textContent =
        payload.message || payload.stdout || payload.stderr || JSON.stringify(payload.raw_output, null, 2);
    }

    document.getElementById("refresh-overview").addEventListener("click", () => loadOverview().catch((error) => setStatus("overview-status", error.message)));
    document.getElementById("search-commands").addEventListener("click", () => searchCommands().catch((error) => setStatus("overview-status", error.message)));
    document.getElementById("search-tools").addEventListener("click", () => searchTools().catch((error) => setStatus("overview-status", error.message)));
    document.getElementById("route-prompt").addEventListener("click", () => routePrompt().catch((error) => setStatus("overview-status", error.message)));
    document.getElementById("bootstrap-prompt").addEventListener("click", () => bootstrapPrompt().catch((error) => setStatus("overview-status", error.message)));
    document.getElementById("load-runtime").addEventListener("click", () => previewRuntime().catch((error) => setStatus("overview-status", error.message)));
    document.getElementById("run-live-claw").addEventListener("click", () => runLiveClaw().catch((error) => {
      document.getElementById("claw-status").textContent = error.message;
    }));

    loadOverview().then(searchCommands).then(searchTools).then(routePrompt).catch((error) => setStatus("overview-status", error.message));
  </script>
</body>
</html>
"""


PROMPT_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Claw Prompt Workspace</title>
  <style>
    :root {
      --bg: #f2eee6;
      --panel: rgba(255, 252, 246, 0.94);
      --ink: #171411;
      --muted: #6b6258;
      --accent: #c65a2f;
      --accent-strong: #a6401e;
      --accent-soft: rgba(198, 90, 47, 0.12);
      --line: rgba(23, 20, 17, 0.1);
      --shadow: 0 24px 70px rgba(69, 43, 19, 0.14);
      --response: #f2e2c5;
      --ok: #244a3d;
      --warn: #7f4c15;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      color: var(--ink);
      font-family: Georgia, "Iowan Old Style", "Palatino Linotype", serif;
      background:
        radial-gradient(circle at top left, rgba(198, 90, 47, 0.16), transparent 30%),
        radial-gradient(circle at bottom right, rgba(36, 74, 61, 0.14), transparent 28%),
        linear-gradient(180deg, #faf6ed 0%, var(--bg) 100%);
    }

    .page {
      width: min(1180px, calc(100vw - 32px));
      margin: 24px auto 40px;
      display: grid;
      gap: 20px;
    }

    .card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 28px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(12px);
    }

    .hero {
      padding: 28px;
      display: grid;
      grid-template-columns: 1.1fr 0.9fr;
      gap: 18px;
      align-items: stretch;
    }

    .eyebrow {
      text-transform: uppercase;
      letter-spacing: 0.18em;
      color: var(--accent-strong);
      font-size: 12px;
      margin-bottom: 10px;
    }

    h1, h2, h3, p {
      margin-top: 0;
    }

    h1 {
      font-size: clamp(34px, 5vw, 62px);
      line-height: 0.94;
      margin-bottom: 14px;
    }

    .lede, .muted, .meta-row {
      color: var(--muted);
    }

    .hero-panel,
    .section {
      padding: 22px;
    }

    .hero-panel {
      background: rgba(255, 255, 255, 0.62);
      border: 1px solid var(--line);
      border-radius: 22px;
    }

    .toolbar {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      align-items: center;
    }

    .toolbar.push {
      justify-content: space-between;
    }

    input, textarea, button, select {
      font: inherit;
    }

    input, textarea, select {
      width: 100%;
      border: 1px solid rgba(23, 20, 17, 0.14);
      border-radius: 18px;
      padding: 14px 16px;
      color: var(--ink);
      background: rgba(255, 255, 255, 0.78);
    }

    textarea {
      min-height: 220px;
      resize: vertical;
    }

    button {
      border: 0;
      border-radius: 999px;
      background: var(--accent);
      color: white;
      padding: 12px 20px;
      cursor: pointer;
      transition: transform 140ms ease, background 140ms ease;
    }

    button.secondary {
      background: #244a3d;
    }

    button.ghost {
      background: rgba(23, 20, 17, 0.08);
      color: var(--ink);
    }

    button:hover {
      transform: translateY(-1px);
      background: var(--accent-strong);
    }

    button.secondary:hover {
      background: #1d3d32;
    }

    button.ghost:hover {
      background: rgba(23, 20, 17, 0.14);
    }

    .grid {
      display: grid;
      grid-template-columns: 1.15fr 0.85fr;
      gap: 20px;
    }

    .control-grid {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 12px;
      margin: 16px 0 18px;
    }

    .status-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border-radius: 999px;
      padding: 8px 14px;
      background: var(--accent-soft);
      color: var(--accent-strong);
      font-size: 13px;
    }

    .status-pill.ok {
      background: rgba(36, 74, 61, 0.12);
      color: var(--ok);
    }

    .status-pill.warn {
      background: rgba(127, 76, 21, 0.14);
      color: var(--warn);
    }

    .prompt-shell {
      display: grid;
      gap: 16px;
    }

    .response-shell {
      display: grid;
      gap: 14px;
    }

    .response-box,
    .history-item,
    .preset {
      border: 1px solid var(--line);
      border-radius: 20px;
      background: rgba(255, 255, 255, 0.58);
    }

    .response-box {
      min-height: 300px;
      padding: 18px;
      background: var(--response);
      white-space: pre-wrap;
      word-break: break-word;
      overflow: auto;
    }

    .history-list,
    .preset-list {
      display: grid;
      gap: 12px;
    }

    .history-item,
    .preset {
      padding: 14px 16px;
    }

    .history-item button,
    .preset button {
      margin-top: 10px;
    }

    .meta-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }

    .meta-row {
      border-radius: 18px;
      border: 1px solid var(--line);
      padding: 12px 14px;
      background: rgba(255, 255, 255, 0.55);
    }

    .meta-row strong {
      display: block;
      color: var(--ink);
      margin-bottom: 4px;
    }

    .subtle-link {
      color: var(--accent-strong);
      text-decoration: none;
    }

    .empty {
      color: var(--muted);
      font-style: italic;
    }

    @media (max-width: 980px) {
      .hero,
      .grid,
      .control-grid,
      .meta-grid {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <div class="page">
    <section class="card hero">
      <div>
        <div class="eyebrow">Claw Prompt Workspace</div>
        <h1>Type a prompt.<br>Get a real response.</h1>
        <p class="lede">This page is purpose-built for actually talking to `claw`, not browsing internals. It uses the live Rust runtime behind the scenes and returns the real response in the browser.</p>
        <div class="toolbar">
          <a class="subtle-link" href="/">Back to control room</a>
        </div>
      </div>
      <div class="hero-panel">
        <div class="eyebrow">Runtime Status</div>
        <div id="runtime-badge" class="status-pill">Checking live runtime...</div>
        <p class="muted" id="runtime-caption" style="margin-top: 14px;">Looking for a built `claw` binary or a cargo fallback.</p>
      </div>
    </section>

    <section class="grid">
      <div class="card section">
        <div class="eyebrow">Prompt Composer</div>
        <div class="prompt-shell">
          <textarea id="prompt-input" placeholder="Ask claw to summarize code, inspect a workflow, draft text, or answer a question.">Summarize what this repository does and call out the major runtime surfaces.</textarea>
          <div class="control-grid">
            <div>
              <div class="eyebrow">Model</div>
              <input id="prompt-model" value="sonnet" placeholder="sonnet">
            </div>
            <div>
              <div class="eyebrow">Permission Mode</div>
              <select id="prompt-permission">
                <option value="read-only" selected>read-only</option>
                <option value="workspace-write">workspace-write</option>
                <option value="danger-full-access">danger-full-access</option>
              </select>
            </div>
            <div>
              <div class="eyebrow">Delivery</div>
              <input id="prompt-label" value="One-shot browser run" placeholder="Optional label">
            </div>
          </div>
          <div class="toolbar push">
            <div class="toolbar">
              <button id="send-prompt">Send Prompt</button>
              <button id="clear-prompt" class="ghost">Clear</button>
            </div>
            <div class="muted">Tip: `Ctrl+Enter` sends the prompt.</div>
          </div>
        </div>
      </div>

      <div class="card section">
        <div class="eyebrow">Prompt Starters</div>
        <div class="preset-list">
          <div class="preset">
            <strong>Codebase summary</strong>
            <div class="muted">Get a fast map of the project and its major components.</div>
            <button class="ghost" data-preset="Summarize this repository and explain the main runtime surfaces.">Use Prompt</button>
          </div>
          <div class="preset">
            <strong>Workflow review</strong>
            <div class="muted">Ask for a practical review of a subsystem or flow.</div>
            <button class="ghost" data-preset="Review the current web UI flow and suggest the next highest-value UX improvement.">Use Prompt</button>
          </div>
          <div class="preset">
            <strong>Docs draft</strong>
            <div class="muted">Generate release notes, summaries, or contributor guidance.</div>
            <button class="ghost" data-preset="Draft concise release notes for the latest branch changes in this repository.">Use Prompt</button>
          </div>
        </div>
      </div>
    </section>

    <section class="grid">
      <div class="card section">
        <div class="eyebrow">Response</div>
        <div class="response-shell">
          <div id="response-status" class="status-pill">Waiting for a prompt.</div>
          <div class="response-box" id="response-output">Your response will appear here.</div>
          <div class="meta-grid">
            <div class="meta-row">
              <strong>Runtime</strong>
              <span id="response-runtime">Not run yet</span>
            </div>
            <div class="meta-row">
              <strong>Duration</strong>
              <span id="response-duration">Not run yet</span>
            </div>
            <div class="meta-row">
              <strong>Model</strong>
              <span id="response-model">Not run yet</span>
            </div>
            <div class="meta-row">
              <strong>Tokens</strong>
              <span id="response-tokens">Not run yet</span>
            </div>
          </div>
        </div>
      </div>

      <div class="card section">
        <div class="eyebrow">Recent Runs</div>
        <div id="history-list" class="history-list">
          <div class="empty">Recent prompts will appear here after you run them.</div>
        </div>
      </div>
    </section>
  </div>

  <script>
    const HISTORY_KEY = "claw-web-ui-history";

    async function fetchJson(url, options) {
      const response = await fetch(url, options);
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `Request failed: ${response.status}`);
      }
      return response.json();
    }

    function setBadge(message, kind = "") {
      const badge = document.getElementById("response-status");
      badge.textContent = message;
      badge.className = `status-pill ${kind}`.trim();
    }

    function setRuntimeBadge(message, caption, kind = "") {
      const badge = document.getElementById("runtime-badge");
      badge.textContent = message;
      badge.className = `status-pill ${kind}`.trim();
      document.getElementById("runtime-caption").textContent = caption;
    }

    function loadHistory() {
      try {
        return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
      } catch {
        return [];
      }
    }

    function saveHistory(entries) {
      localStorage.setItem(HISTORY_KEY, JSON.stringify(entries.slice(0, 6)));
    }

    function renderHistory() {
      const history = loadHistory();
      const list = document.getElementById("history-list");
      list.innerHTML = "";
      if (!history.length) {
        list.innerHTML = '<div class="empty">Recent prompts will appear here after you run them.</div>';
        return;
      }

      for (const entry of history) {
        const item = document.createElement("div");
        item.className = "history-item";
        item.innerHTML = `
          <strong>${entry.label}</strong>
          <div class="muted" style="margin-top: 6px;">${entry.prompt}</div>
          <div class="muted" style="margin-top: 8px;">${entry.model} · ${entry.permission_mode} · ${entry.duration_ms} ms</div>
          <button class="ghost">Reuse Prompt</button>
        `;
        item.querySelector("button").addEventListener("click", () => {
          document.getElementById("prompt-input").value = entry.prompt;
          document.getElementById("prompt-model").value = entry.model;
          document.getElementById("prompt-permission").value = entry.permission_mode;
          document.getElementById("prompt-label").value = entry.label;
        });
        list.appendChild(item);
      }
    }

    async function loadOverview() {
      const payload = await fetchJson("/api/overview");
      const claw = payload.claw_runtime;
      if (claw.available) {
        setRuntimeBadge(
          `Live claw ready via ${claw.strategy}`,
          `Using ${claw.command_path}`,
          "ok"
        );
      } else {
        setRuntimeBadge(
          "Live claw unavailable",
          claw.reason || "No runtime found.",
          "warn"
        );
      }
    }

    function applyPayload(payload) {
      const raw = payload.raw_output || {};
      const usage = raw.usage || {};
      document.getElementById("response-output").textContent =
        payload.message || payload.stdout || payload.stderr || JSON.stringify(payload, null, 2);
      document.getElementById("response-runtime").textContent =
        payload.runtime ? `${payload.runtime.strategy} at ${payload.runtime.command_path}` : "Unavailable";
      document.getElementById("response-duration").textContent = `${payload.duration_ms || 0} ms`;
      document.getElementById("response-model").textContent = raw.model || payload.model || "Unknown";
      const inputTokens = usage.input_tokens ?? "n/a";
      const outputTokens = usage.output_tokens ?? "n/a";
      document.getElementById("response-tokens").textContent = `${inputTokens} in / ${outputTokens} out`;
    }

    async function sendPrompt() {
      const prompt = document.getElementById("prompt-input").value.trim();
      const model = document.getElementById("prompt-model").value.trim() || "sonnet";
      const permissionMode = document.getElementById("prompt-permission").value.trim() || "read-only";
      const label = document.getElementById("prompt-label").value.trim() || "Browser prompt";

      if (!prompt) {
        setBadge("Enter a prompt before sending it.", "warn");
        return;
      }

      setBadge("Running prompt through live claw...", "");
      document.getElementById("response-output").textContent = "Waiting for response...";

      const payload = await fetchJson("/api/claw", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt,
          model,
          permission_mode: permissionMode,
        }),
      });

      applyPayload(payload);
      setBadge(`Response delivered in ${payload.duration_ms} ms.`, payload.ok ? "ok" : "warn");

      const history = loadHistory();
      history.unshift({
        label,
        prompt,
        model,
        permission_mode: permissionMode,
        duration_ms: payload.duration_ms || 0,
      });
      saveHistory(history);
      renderHistory();
    }

    function wirePresets() {
      for (const button of document.querySelectorAll("[data-preset]")) {
        button.addEventListener("click", () => {
          document.getElementById("prompt-input").value = button.dataset.preset || "";
        });
      }
    }

    document.getElementById("send-prompt").addEventListener("click", () => {
      sendPrompt().catch((error) => {
        setBadge(error.message, "warn");
        document.getElementById("response-output").textContent = error.message;
      });
    });

    document.getElementById("clear-prompt").addEventListener("click", () => {
      document.getElementById("prompt-input").value = "";
      document.getElementById("response-output").textContent = "Your response will appear here.";
      setBadge("Waiting for a prompt.");
    });

    document.getElementById("prompt-input").addEventListener("keydown", (event) => {
      if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
        event.preventDefault();
        sendPrompt().catch((error) => {
          setBadge(error.message, "warn");
          document.getElementById("response-output").textContent = error.message;
        });
      }
    });

    wirePresets();
    renderHistory();
    loadOverview().catch((error) => {
      setRuntimeBadge("Live claw unavailable", error.message, "warn");
    });
  </script>
</body>
</html>
"""


def _module_to_dict(module: Any) -> dict[str, Any]:
    return asdict(module)


def build_overview_payload() -> dict[str, Any]:
    manifest = build_port_manifest()
    return {
        "manifest": {
            "src_root": str(manifest.src_root),
            "total_python_files": manifest.total_python_files,
            "top_level_modules": [_module_to_dict(module) for module in manifest.top_level_modules],
        },
        "commands": {"total": len(PORTED_COMMANDS)},
        "tools": {"total": len(PORTED_TOOLS)},
        "claw_runtime": claw_runtime_payload(),
    }


def search_commands_payload(query: str | None = None, limit: int = 12) -> dict[str, Any]:
    entries = find_commands(query, limit) if query else list(PORTED_COMMANDS[:limit])
    return {
        "query": query or "",
        "total": len(PORTED_COMMANDS),
        "entries": [_module_to_dict(entry) for entry in entries],
    }


def search_tools_payload(query: str | None = None, limit: int = 12) -> dict[str, Any]:
    entries = find_tools(query, limit) if query else list(PORTED_TOOLS[:limit])
    return {
        "query": query or "",
        "total": len(PORTED_TOOLS),
        "entries": [_module_to_dict(entry) for entry in entries],
    }


def route_prompt_payload(prompt: str, limit: int = 6) -> dict[str, Any]:
    runtime = PortRuntime()
    matches = runtime.route_prompt(prompt, limit=limit)
    return {
        "prompt": prompt,
        "matches": [_module_to_dict(match) for match in matches],
    }


def bootstrap_prompt_payload(prompt: str, limit: int = 6) -> dict[str, Any]:
    session = PortRuntime().bootstrap_session(prompt, limit=limit)
    return {
        "prompt": prompt,
        "turn_output": session.turn_result.output,
        "stop_reason": session.turn_result.stop_reason,
        "matched_commands": list(session.turn_result.matched_commands),
        "matched_tools": list(session.turn_result.matched_tools),
        "usage": {
            "input_tokens": session.turn_result.usage.input_tokens,
            "output_tokens": session.turn_result.usage.output_tokens,
        },
        "persisted_session_path": session.persisted_session_path,
        "markdown": session.as_markdown(),
    }


def claw_runtime_payload(repo_root: Path | None = None) -> dict[str, Any]:
    rust_root = (repo_root or REPO_ROOT) / "rust"
    executable_candidates = [
        rust_root / "target" / "debug" / "claw",
        rust_root / "target" / "release" / "claw",
        rust_root / "target" / "debug" / "claw.exe",
        rust_root / "target" / "release" / "claw.exe",
    ]
    for candidate in executable_candidates:
        if candidate.exists():
            return {
                "available": True,
                "strategy": "binary",
                "command_path": str(candidate),
                "cwd": str(rust_root),
            }

    cargo = shutil.which("cargo")
    if cargo and (rust_root / "Cargo.toml").exists():
        return {
            "available": True,
            "strategy": "cargo-run",
            "command_path": cargo,
            "cwd": str(rust_root),
        }

    return {
        "available": False,
        "strategy": "unavailable",
        "command_path": "",
        "cwd": str(rust_root),
        "reason": "no built claw binary or cargo toolchain found",
    }


def claw_prompt_payload(
    prompt: str,
    model: str = DEFAULT_CLAW_MODEL,
    permission_mode: str = DEFAULT_CLAW_PERMISSION_MODE,
    repo_root: Path | None = None,
    runner: Any = None,
) -> dict[str, Any]:
    runtime = claw_runtime_payload(repo_root)
    if not runtime["available"]:
        return {
            "ok": False,
            "prompt": prompt,
            "runtime": runtime,
            "error": runtime["reason"],
        }

    command = _claw_command(runtime, prompt, model, permission_mode)
    env = os.environ.copy()
    env.update(load_project_env((repo_root or REPO_ROOT) / "rust" / ".env"))
    runner = runner or subprocess.run
    started = time_now_ms()
    completed = runner(
        command,
        cwd=runtime["cwd"],
        env=env,
        capture_output=True,
        text=True,
        timeout=CLAW_TIMEOUT_SECONDS,
        check=False,
    )
    duration_ms = time_now_ms() - started
    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    parsed = None
    message = stdout
    if stdout:
        try:
            parsed = json.loads(stdout)
            if isinstance(parsed, dict):
                message = str(parsed.get("message") or stdout)
        except json.JSONDecodeError:
            parsed = None

    return {
        "ok": completed.returncode == 0,
        "prompt": prompt,
        "model": model,
        "permission_mode": permission_mode,
        "runtime": runtime,
        "command": command,
        "duration_ms": duration_ms,
        "returncode": completed.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "message": message,
        "raw_output": parsed,
        "error": stderr if completed.returncode != 0 else None,
    }


def _claw_command(
    runtime: dict[str, Any],
    prompt: str,
    model: str,
    permission_mode: str,
) -> list[str]:
    command_prefix = [runtime["command_path"]]
    if runtime["strategy"] == "cargo-run":
        command_prefix = [runtime["command_path"], "run", "-q", "-p", "rusty-claude-cli", "--"]
    return [
        *command_prefix,
        "--model",
        model,
        "--permission-mode",
        permission_mode,
        "--output-format",
        "json",
        prompt,
    ]


def load_project_env(env_path: Path) -> dict[str, str]:
    if not env_path.exists():
        return {}
    loaded: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        # Normalize whitespace both before and after quote removal so simple
        # `.env` files load cleanly into subprocess environments.
        value = value.strip().strip('"').strip("'").strip()
        if value.endswith("\\n"):
            value = value[:-2].strip()
        loaded[key.strip()] = value
    return loaded


def time_now_ms() -> int:
    return int(time.time() * 1000)


class ClawWebUiServer(ThreadingHTTPServer):
    daemon_threads = True


class ClawWebUiHandler(BaseHTTPRequestHandler):
    server_version = "ClawWebUi/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_html(HTML_PAGE)
            return
        if parsed.path == "/prompt":
            self._send_html(PROMPT_PAGE)
            return
        if parsed.path == "/api/overview":
            self._send_json(build_overview_payload())
            return
        if parsed.path == "/api/commands":
            params = parse_qs(parsed.query)
            self._send_json(
                search_commands_payload(
                    params.get("q", [""])[0] or None,
                    _parse_limit(params.get("limit", ["12"])[0]),
                )
            )
            return
        if parsed.path == "/api/tools":
            params = parse_qs(parsed.query)
            self._send_json(
                search_tools_payload(
                    params.get("q", [""])[0] or None,
                    _parse_limit(params.get("limit", ["12"])[0]),
                )
            )
            return
        if parsed.path == "/api/route":
            params = parse_qs(parsed.query)
            prompt = params.get("prompt", [""])[0]
            self._send_json(route_prompt_payload(prompt, _parse_limit(params.get("limit", ["6"])[0])))
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path not in {"/api/bootstrap", "/api/claw"}:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            prompt = str(payload.get("prompt", "")).strip()
            if parsed.path == "/api/bootstrap":
                limit = _parse_limit(payload.get("limit", 6))
                self._send_json(bootstrap_prompt_payload(prompt, limit))
                return
            model = str(payload.get("model", DEFAULT_CLAW_MODEL)).strip() or DEFAULT_CLAW_MODEL
            permission_mode = (
                str(payload.get("permission_mode", DEFAULT_CLAW_PERMISSION_MODE)).strip()
                or DEFAULT_CLAW_PERMISSION_MODE
            )
            result = claw_prompt_payload(
                prompt,
                model=model,
                permission_mode=permission_mode,
            )
            status = HTTPStatus.OK if result["ok"] else HTTPStatus.BAD_GATEWAY
            self._send_json(result, status=status)
        except Exception as error:  # pragma: no cover - request safety net
            self._send_json({"ok": False, "error": str(error)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_html(self, payload: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = payload.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _parse_limit(value: Any) -> int:
    try:
        return max(1, min(int(value), 24))
    except (TypeError, ValueError):
        return 12


def advertised_urls(host: str, port: int) -> list[str]:
    if host in {"0.0.0.0", "::", ""}:
        urls = [f"http://127.0.0.1:{port}"]
        for address in local_ipv4_addresses():
            urls.append(f"http://{address}:{port}")
        return urls
    return [f"http://{host}:{port}"]


def local_ipv4_addresses() -> list[str]:
    addresses: set[str] = set()
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM):
            address = info[4][0]
            if not address.startswith("127."):
                addresses.add(address)
    except OSError:
        pass

    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        address = probe.getsockname()[0]
        if address and not address.startswith("127."):
            addresses.add(address)
    except OSError:
        pass
    finally:
        probe.close()

    return sorted(addresses)


def run_web_ui(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = False) -> int:
    server = ClawWebUiServer((host, port), ClawWebUiHandler)
    urls = advertised_urls(host, port)
    print("Claw Code web UI running at:")
    for url in urls:
        print(f"  - {url}")
    if open_browser:
        threading.Thread(target=lambda: webbrowser.open(urls[0]), daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
