# Contributing

Claw Code has two active surfaces in this repository:

- the canonical Rust workspace in [`rust/`](./rust)
- the Python companion workspace in [`src/`](./src) and [`tests/`](./tests), including the browser-based control room

This guide keeps contribution flow practical and aligned with the current repo shape.

## Before you start

1. Read [`README.md`](./README.md) for the repo map.
2. Use [`USAGE.md`](./USAGE.md) for the current CLI and auth workflow.
3. Check [`PARITY.md`](./PARITY.md) if your change touches Rust-port coverage or parity claims.

## Local setup

### Rust workspace

```bash
cd rust
cargo build --workspace
./target/debug/claw --help
```

Auth for live provider flows:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Python companion workspace

```bash
python -m src.main summary
python -m unittest tests.test_porting_workspace
```

### Web UI

```bash
python -m src.main web-ui --port 8765
```

LAN mode:

```bash
python -m src.main web-ui --lan --port 8765
```

## Project structure

- [`rust/`](./rust) holds the canonical `claw` runtime and CLI
- [`src/`](./src) mirrors command, tool, and runtime concepts for audit, exploration, and the web UI
- [`tests/`](./tests) covers the Python workspace and integration helpers
- [`docs/`](./docs) holds focused guides for architecture, development, container use, and the web UI

## What to test

Match the test scope to the change:

- Rust CLI/runtime changes:

```bash
cd rust
cargo test --workspace
```

- Python workspace or web UI changes:

```bash
python -m unittest tests.test_porting_workspace
```

- Live runtime bridge changes:
  - build the Rust binary under `rust/target/debug/claw`
  - run the Python test suite
  - smoke test `python -m src.main web-ui --port 8765`

## Documentation expectations

Update docs when you change:

- top-level workflows in [`README.md`](./README.md) or [`USAGE.md`](./USAGE.md)
- browser UI behavior in [`docs/web-ui.md`](./docs/web-ui.md)
- repository layout or boundaries in [`docs/architecture.md`](./docs/architecture.md)
- contributor workflow in this file

## Repo hygiene

- Do not commit secrets such as `.env` files or provider keys.
- Do not commit generated session artifacts under `.port_sessions/`.
- Keep changes scoped. If you touch both Rust and Python, make sure the docs explain the cross-surface behavior.
- Prefer tests that verify current behavior instead of snapshots that drift silently.

## Branching and pushing

- Use a feature branch for non-trivial work.
- Push only after the relevant tests pass locally.
- If you cannot push to the upstream remote, push to your fork and open a PR from there.
