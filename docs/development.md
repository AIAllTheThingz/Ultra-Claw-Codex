# Development Workflow

This project is easiest to work with if you treat the Rust and Python surfaces as complementary, not interchangeable.

## Recommended daily flow

1. Make the Rust workspace build cleanly.
2. Run the Python companion tests if you touched `src/`, `tests/`, or the web UI.
3. Update the docs when the user-facing workflow changes.

## Rust workflow

Build and test:

```bash
cd rust
cargo build --workspace
cargo test --workspace
```

Useful spot checks:

```bash
./target/debug/claw --help
./target/debug/claw status
./target/debug/claw doctor
./target/debug/claw --output-format json prompt "status"
```

Live auth flow:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
./target/debug/claw prompt "reply with ready"
```

## Python workflow

The Python workspace mirrors command and tool metadata and powers the browser UI.

Quick checks:

```bash
python -m src.main summary
python -m src.main commands --limit 10 --query review
python -m src.main tools --limit 10 --query MCP
python -m unittest tests.test_porting_workspace
```

## Web UI workflow

Local:

```bash
python -m src.main web-ui --port 8765
```

LAN:

```bash
python -m src.main web-ui --lan --port 8765
```

The UI exposes:

- workspace overview
- command and tool search
- prompt routing
- bootstrap preview
- live one-shot execution against the real Rust `claw` binary when available

If `rust/target/debug/claw` exists, the UI uses it directly. Otherwise it falls back to cargo when possible.

## Generated artifacts

Keep generated local artifacts out of commits:

- `.port_sessions/`
- local `.env` files
- per-user auth state

## When to update docs

Update the docs in the same change when you alter:

- startup commands
- auth or model configuration
- web UI behavior
- repo structure or contributor workflow

This repo moves quickly, so small documentation updates with each feature are better than large catch-up passes later.
