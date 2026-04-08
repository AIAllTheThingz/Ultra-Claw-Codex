# Ultra-Claw-Codex

Ultra-Claw-Codex is an AI-assisted CLI and browser workspace built around the Rust `claw` runtime, with a companion Python control layer for inspection, routing, testing, and a LAN-accessible web UI.

This repository currently gives you two practical ways to use the project:

- the canonical Rust CLI in [`rust/`](./rust)
- a browser UI in [`src/server/web_ui.py`](./src/server/web_ui.py) that can call the real Rust `claw` binary for one-shot prompts

> [!IMPORTANT]
> If you are setting this up for the first time, read the [First Run Instructions](#first-run-instructions) section below before anything else.

## Table of Contents

- [What It Does](#what-it-does)
- [Prerequisites](#prerequisites)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Deployment Instructions](#deployment-instructions)
- [First Run Instructions](#first-run-instructions)
- [Potential Issues](#potential-issues)
- [Troubleshooting](#troubleshooting)
- [Documentation Map](#documentation-map)

## What It Does

Ultra-Claw-Codex provides:

- a Rust-based `claw` CLI for prompts, sessions, runtime inspection, and agent-style workflows
- a Python companion workspace that mirrors command and tool metadata for visibility and audit workflows
- a browser UI for:
  - workspace overview
  - command and tool search
  - prompt routing previews
  - bootstrap/runtime previews
  - dedicated prompt entry and live response delivery through the actual Rust `claw` binary
- LAN hosting support so the browser UI can be used from other devices on your internal network

In short, this repo is both a working AI runtime and a usability layer around that runtime.

## Prerequisites

These are practical recommendations for running the repo comfortably, especially if you want the Rust CLI, tests, and browser UI all available on the same box.

### Operating System

Supported and practical options:

- Ubuntu 22.04+ or similar modern Linux distribution
- Windows 11 with PowerShell for local development
- macOS should be workable for development, but the current deployment and validation work in this repo have primarily been exercised on Linux and Windows

Recommended deployment target:

- Linux host on your internal network if you want the LAN web UI and stable Rust runtime path

### Disk Space

Recommended:

- minimum: `10 GB` free
- comfortable working space: `20 GB+`

Why:

- Rust workspace builds and test artifacts
- Python environment and support files
- Git history, logs, generated build outputs, and temporary runtime artifacts

### RAM

Recommended:

- minimum: `8 GB`
- preferred: `16 GB+`

Why:

- Rust compilation can be memory-hungry
- running the web UI, local tests, and development tools together is smoother with more headroom

### Required Software

- `git`
- Rust toolchain via `rustup`
- Python 3.11+ recommended
- network access for live model/provider calls

### Auth / API Access

One of the following is required for live prompt execution:

- `ANTHROPIC_API_KEY`
- `claw login` OAuth flow where supported

## Tech Stack

Core technologies in this repository:

- Rust
  - canonical runtime and CLI implementation
- Python
  - companion workspace, testing, and web UI server
- HTML/CSS/JavaScript
  - lightweight browser UI served directly from Python
- PowerShell / Bash
  - development, deployment, and verification workflows

Major components:

- Rust crates for runtime, API/provider clients, commands, tools, plugins, telemetry, and CLI execution
- Python modules for workspace inspection, mirrored routing, bootstrapping, remote-mode helpers, and browser delivery
- JSON and Markdown documentation for usage, parity, planning, and contributor workflows

## Project Structure

Top-level repository layout:

- [`rust/`](./rust)
  - canonical Rust implementation of `claw`
- [`src/`](./src)
  - Python companion workspace and browser UI server
- [`tests/`](./tests)
  - Python-side verification for the mirrored workspace and web UI
- [`docs/`](./docs)
  - focused docs for architecture, development, web UI, and container workflows
- [`USAGE.md`](./USAGE.md)
  - task-oriented commands and runtime usage
- [`CONTRIBUTING.md`](./CONTRIBUTING.md)
  - contributor workflow and repo hygiene
- [`PARITY.md`](./PARITY.md)
  - parity and migration tracking
- [`ROADMAP.md`](./ROADMAP.md)
  - roadmap and cleanup direction

Important implementation files:

- [`src/main.py`](./src/main.py)
  - Python CLI entrypoint
- [`src/server/web_ui.py`](./src/server/web_ui.py)
  - browser UI and live runtime bridge
- [`tests/test_porting_workspace.py`](./tests/test_porting_workspace.py)
  - Python-side test coverage

## Deployment Instructions

This repo can be used as a development checkout or deployed as a LAN-accessible internal tool.

### 1. Clone the repository

```bash
git clone https://github.com/AIAllTheThingz/Ultra-Claw-Codex.git
cd Ultra-Claw-Codex
```

### 2. Prepare Rust

If Rust is not already installed:

```bash
curl https://sh.rustup.rs -sSf | sh
source ~/.cargo/env
```

Install common build dependencies on Ubuntu:

```bash
sudo apt update
sudo apt install -y build-essential pkg-config libssl-dev git python3 python3-pip
```

### 3. Build the Rust workspace

```bash
cd rust
cargo build --workspace
```

This produces the CLI binary at:

- debug build: `rust/target/debug/claw`
- release build: `rust/target/release/claw`

### 4. Configure auth

Example API key setup:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Optional project-local `.env` file for the browser UI and local workflows:

```bash
cd rust
printf 'ANTHROPIC_API_KEY=%s\n' 'sk-ant-...' > .env
chmod 600 .env
```

### 5. Start the browser UI

Local only:

```bash
cd ..
python -m src.main web-ui --port 8765
```

Internal network / LAN:

```bash
python -m src.main web-ui --lan --port 8765
```

Open:

- local: `http://127.0.0.1:8765`
- LAN example: `http://192.168.1.73:8765`

Dedicated prompt page:

- `http://<host>:8765/prompt`

## First Run Instructions

Use this exact order for a clean first run.

### Step 1. Build the Rust binary

```bash
cd rust
cargo build --workspace
```

### Step 2. Check the CLI health

```bash
./target/debug/claw --help
./target/debug/claw status
./target/debug/claw doctor
```

### Step 3. Run a one-shot prompt from the terminal

```bash
./target/debug/claw --model sonnet --permission-mode read-only --output-format json "Reply with exactly: ready"
```

### Step 4. Start the browser UI

From the repo root:

```bash
python -m src.main web-ui --port 8765
```

### Step 5. Open the prompt page

Open:

- `http://127.0.0.1:8765/prompt`

Then:

- enter a prompt
- choose a model
- choose a permission mode
- submit

The page should return the live response from the Rust runtime.

### Step 6. Run the Python verification suite

From the repo root:

```bash
python -m unittest tests.test_porting_workspace
```

### Step 7. Run the Rust test suite

```bash
cd rust
cargo test --workspace
```

## Potential Issues

These are the most likely things to go wrong in real usage.

### 1. `cargo` or `rustc` not found

Cause:

- Rust not installed
- shell did not load `~/.cargo/env`

### 2. Live prompt returns auth errors

Cause:

- missing or invalid `ANTHROPIC_API_KEY`
- stale `.env`
- wrong shell environment

### 3. Browser UI loads but live prompt execution fails

Cause:

- Rust binary not built yet
- no `cargo` fallback available
- auth missing
- provider/model unavailable

### 4. LAN UI not reachable from another device

Cause:

- server started without `--lan`
- host firewall blocking the port
- wrong IP address
- service bound on the wrong machine

### 5. Slow prompt responses

Cause:

- live provider latency
- larger prompt payloads
- slower model
- network delay

### 6. Port already in use

Cause:

- an older web UI instance is still listening on `8765`

## Troubleshooting

### Rust not on PATH

```bash
source ~/.cargo/env
rustc --version
cargo --version
```

### Verify the `claw` binary exists

```bash
cd rust
ls -l target/debug/claw
```

If missing:

```bash
cargo build -p rusty-claude-cli
```

### Verify the browser UI test coverage

```bash
python -m unittest tests.test_porting_workspace
```

### Check the web UI is listening

Linux:

```bash
ss -ltn | grep 8765
```

Windows PowerShell:

```powershell
netstat -ano | findstr 8765
```

### Test the live runtime API directly

```bash
curl -X POST http://127.0.0.1:8765/api/claw \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Reply with exactly: ready","model":"sonnet","permission_mode":"read-only"}'
```

### Fix auth issues

Check the environment:

```bash
env | grep ANTHROPIC
```

Or if using a project-local file:

```bash
cd rust
cat .env
```

Then retry with a known-good prompt:

```bash
./target/debug/claw --model sonnet --permission-mode read-only --output-format json "Reply with exactly: ready"
```

### Fix LAN access issues

Make sure the UI was started with:

```bash
python -m src.main web-ui --lan --port 8765
```

Then confirm the correct host IP and allow the port through the local firewall.

### Fix port conflicts

Linux:

```bash
fuser -n tcp 8765
kill <pid>
```

Windows PowerShell:

```powershell
netstat -ano | findstr 8765
taskkill /PID <pid> /F
```

## Documentation Map

- [`USAGE.md`](./USAGE.md)
  - CLI, auth, runtime commands, verification
- [`docs/README.md`](./docs/README.md)
  - documentation hub
- [`docs/web-ui.md`](./docs/web-ui.md)
  - browser UI and live runtime bridge
- [`docs/development.md`](./docs/development.md)
  - day-to-day development workflow
- [`docs/architecture.md`](./docs/architecture.md)
  - repository boundaries and runtime surfaces
- [`CONTRIBUTING.md`](./CONTRIBUTING.md)
  - contribution workflow and repo hygiene
- [`rust/README.md`](./rust/README.md)
  - Rust workspace details
- [`PARITY.md`](./PARITY.md)
  - parity and migration status

## Notes

- The browser UI currently prefers the debug binary path first when both debug and release builds are present.
- For active development, `rust/target/debug/claw` is normal and expected.
- For a more appliance-like deployment, you can build and prefer a release binary later.

## Disclaimer

- This repository is an independent project and is not affiliated with, endorsed by, or maintained by Anthropic.
- Protect your API keys and never commit local `.env` files or secrets.
