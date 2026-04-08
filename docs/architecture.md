# Architecture Overview

Claw Code currently ships as a Rust-first CLI project with a Python companion workspace that mirrors parts of the command and tool surface for analysis, auditing, and the browser UI.

## Primary runtime surfaces

### Rust workspace

[`../rust/`](../rust) is the canonical product surface.

Key crates:

- `rusty-claude-cli` — the `claw` binary, REPL, one-shot prompt mode, output formatting
- `runtime` — prompt assembly, config, sessions, permissions, MCP/runtime orchestration
- `api` — provider clients, streaming, preflight request sizing
- `commands` — slash-command registry and help text rendering
- `tools` — tool specs and execution wiring
- `plugins`, `telemetry`, `compat-harness`, `mock-anthropic-service` — supporting surfaces

### Python companion workspace

[`../src/`](../src) and [`../tests/`](../tests) are a mirrored support layer used for:

- workspace inventory and summaries
- parity and audit helpers
- command and tool lookup
- lightweight runtime/bootstrap previews
- the browser-based control room

This Python layer is not the canonical `claw` runtime. It is a support surface around the Rust implementation.

## Web UI boundary

The browser UI lives in [`../src/server/web_ui.py`](../src/server/web_ui.py).

It has two roles:

- expose the mirrored Python workspace via JSON and HTML
- optionally call the real Rust `claw` binary for one-shot prompt execution

That means the UI is a bridge, not a second implementation of the agent loop.

## Runtime bridge to real `claw`

When available, the web UI detects the Rust CLI in this order:

1. `rust/target/debug/claw`
2. `rust/target/release/claw`
3. cargo fallback for `rusty-claude-cli`

For live browser execution it runs the real binary in the Rust workspace with JSON output enabled, then returns the parsed result to the browser.

The bridge reads project-local environment values from `rust/.env` when present. Keep that file local-only and out of Git.

## Repository layout

- [`../README.md`](../README.md) — project entrypoint
- [`../USAGE.md`](../USAGE.md) — user-facing CLI workflows
- [`../docs/`](./README.md) — focused guides
- [`../rust/`](../rust) — canonical implementation
- [`../src/`](../src) — Python mirrored workspace and web UI
- [`../tests/`](../tests) — Python verification
- [`../assets/`](../assets) — repository assets

## Testing layers

### Rust

```bash
cd rust
cargo test --workspace
```

### Python companion workspace

```bash
python -m unittest tests.test_porting_workspace
```

### Live browser-to-runtime smoke path

1. Build `rust/target/debug/claw`
2. Start the UI with `python -m src.main web-ui --port 8765`
3. Run a one-shot prompt from the `Live Claw` panel

## Operational note

The cleanest mental model for this repository is:

- Rust is the product
- Python is the visibility and support layer
- the web UI is the bridge that makes both easier to inspect and operate
