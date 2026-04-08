# Web UI Guide

The Python companion workspace includes a lightweight browser UI for inspecting the project and driving the real Rust `claw` binary.

Source: [`../src/server/web_ui.py`](../src/server/web_ui.py)

## What it does

The UI provides:

- workspace overview and module counts
- command search
- tool search
- prompt-routing previews
- bootstrap/runtime session previews
- a dedicated `/prompt` page for entering a prompt and receiving a real response from the Rust CLI
- a `Live Claw` panel in the control room for one-shot runtime testing

## Start the UI locally

```bash
python -m src.main web-ui --port 8765
```

Open:

- `http://127.0.0.1:8765`
- `http://127.0.0.1:8765/prompt`

## Expose it to your internal network

```bash
python -m src.main web-ui --lan --port 8765
```

The server binds to `0.0.0.0` and prints the reachable local addresses it detects. Example:

```text
Claw Code web UI running at:
  - http://127.0.0.1:8765
  - http://192.168.1.73:8765
```

Dedicated prompt page on LAN:

```text
http://192.168.1.73:8765/prompt
```

## Real `claw` runtime bridge

The browser prompt workflow does not simulate responses. Both the dedicated `/prompt` page and the control-room `Live Claw` panel try to execute the actual Rust CLI from the repository.

Detection order:

1. `rust/target/debug/claw`
2. `rust/target/release/claw`
3. cargo fallback via `rusty-claude-cli`

The bridge runs a one-shot command with JSON output:

```text
claw --model <model> --permission-mode <mode> --output-format json "<prompt>"
```

## Requirements for live execution

- the Rust workspace is present under `rust/`
- either a built `claw` binary exists or `cargo` is available
- auth is configured for the Rust CLI

Project-local environment values can be supplied in `rust/.env`, for example:

```bash
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-6
```

Keep that file local-only.

## Verification

Python coverage for the UI lives in [`../tests/test_porting_workspace.py`](../tests/test_porting_workspace.py).

Run:

```bash
python -m unittest tests.test_porting_workspace
```

For a live smoke test:

1. Build the Rust binary:

```bash
cd rust
cargo build -p rusty-claude-cli
```

2. Start the UI:

```bash
python -m src.main web-ui --port 8765
```

3. Open `http://127.0.0.1:8765/prompt`
4. Submit a short prompt such as `Reply with exactly: ready`

## Security notes

- `--lan` is for trusted internal networks only.
- Anyone who can reach the UI can submit prompts through the live runtime bridge.
- Prefer `read-only` permission mode unless you intentionally need writes.
- If you expose the UI beyond localhost, make sure your host firewall only allows the intended network.
