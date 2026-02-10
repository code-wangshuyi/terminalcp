# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

terminalcp is a Python MCP (Model Context Protocol) server that enables AI agents to spawn and control interactive command-line tools via virtual terminals. It's like Playwright but for the terminal — debug with LLDB/GDB/pdb, interact with REPLs, monitor builds, and control any interactive CLI.

## Build & Development

```bash
# Install for development (editable)
pip install -e .

# Build distribution
python -m build

# Run the CLI
terminalcp --help

# Start as MCP server (stdio, used by Claude Desktop/VS Code/Cursor)
terminalcp --mcp

# Start the background daemon server directly
terminalcp --server
```

**No test framework or linter is configured.** Test manually via CLI commands or the Python API.

## Architecture

**Layered client-server design over Unix domain sockets:**

```
MCP Clients (Claude Desktop, VS Code, Cursor)
    │ stdio
    ▼
mcp_server.py ─── FastMCP wrapper, single "terminalcp" tool
    │
    ▼
terminal_client.py ─── Unix socket client, auto-starts server
    │ ~/.terminalcp/server.sock (line-delimited JSON)
    ▼
terminal_server.py ─── Daemon, multiplexes requests, broadcasts output events
    │
    ▼
terminal_manager.py ─── Core: PTY lifecycle, pyte terminal emulation, I/O
    │
    ▼
Background Processes (PTY slaves, bash -c "command")
```

### Key modules

- **`terminal_manager.py`** — Core process management. Creates PTY pairs via `pty.openpty()`, manages `ManagedTerminal` dataclass (subprocess, pyte screen, raw output buffer, locks). Two output modes: `stdout` (rendered terminal screen via pyte) and `stream` (raw text).
- **`terminal_server.py`** — Async Unix socket daemon at `~/.terminalcp/server.sock`. Handles JSON request-response + event broadcasting to subscribed clients. Routes actions to TerminalManager.
- **`terminal_client.py`** — Client that auto-connects and auto-starts the daemon. Uses asyncio Futures for request tracking with 5-second timeout.
- **`mcp_server.py`** — Thin FastMCP adapter. Exposes one tool (`terminalcp`) that delegates to TerminalClient. All MCP actions: start, stop, stdout, stdin, stream, list, term-size, claude-status, kill-server.
- **`cli.py`** — CLI dispatcher with subcommands: list, start, stop, status, stdout, stream, stdin, resize, attach, version, kill-server.
- **`claude_status.py`** — Claude Code CLI state detection. Parses rendered terminal output to detect processing/interactive/completed/idle states and plan/accept-edits/default prompt modes.
- **`attach_client.py`** — Interactive terminal attachment with raw mode, SIGWINCH handling, and Ctrl+B detach.
- **`key_parser.py`** — Translates special key notation (e.g., `::Up`, `::C-c`, `::Tab`) to ANSI escape sequences.
- **`completion/`** — Shell completion scripts for bash, zsh, fish.

### Key patterns

- **IPC Protocol**: Line-delimited JSON over Unix socket. Messages have `type` (request/response/event), requests have `id` for Future resolution.
- **Terminal emulation**: `pyte.HistoryScreen` (10K scrollback) + `pyte.Stream`/`pyte.ByteStream` for VT-100 rendering.
- **Concurrency**: `asyncio.Lock` on PTY input writes, `threading.Lock` on screen/output reads.
- **PTY setup**: Non-blocking master FD with `asyncio.add_reader()`, env includes `TERM=xterm-256color`.
- **Input delay**: 200ms delay after `\r` (Enter) to prevent command buffering issues.

## Dependencies

- `mcp` (>=1.0.0) — Model Context Protocol framework (FastMCP)
- `pyte` (>=0.8.2) — Virtual terminal emulation
- Build backend: hatchling

## CI/CD

GitHub Actions publishes to PyPI on release (`publish.yml`). Uses OIDC authentication.
