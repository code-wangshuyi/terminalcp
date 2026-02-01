# terminalcp

Python port of [terminalcp](https://github.com/badlogic/terminalcp) — let AI agents control interactive command-line tools like a human would.

## What it does

terminalcp enables AI agents to spawn and interact with any CLI tool in real-time — from debuggers like LLDB and GDB to other AI coding assistants like Claude Code, Gemini CLI, and Codex. Think of it as Playwright for the terminal: your agent can start processes, send keystrokes, read output, and maintain full interactive sessions with tools that normally require human input.

Key capabilities:
- Debug code step-by-step using command-line debuggers (LLDB, GDB, pdb)
- Collaborate with other AI tools by running them as subprocesses
- Interact with REPLs (Python, Node, Ruby), database shells, and system monitors
- Control any interactive CLI that expects human input
- Run multiple processes simultaneously without blocking the agent
- Users can attach to AI-spawned processes from their own terminal, similar to screen/tmux

Two output modes for different use cases:
- **Terminal mode (stdout)**: Returns the rendered screen with full scrollback — perfect for TUIs like vim, htop, or interactive debuggers where visual layout matters
- **Stream mode**: Returns raw output with optional ANSI stripping and incremental reading — ideal for build processes, server logs, and high-volume output

Each process runs in a proper pseudo-TTY with full terminal emulation (via [pyte](https://github.com/selectel/pyte)), preserving colors, cursor movement, and special key sequences. Processes run in the background, so your agent stays responsive while managing long-running tools.

## Requirements

- Python 3.10 or newer
- An MCP client (VS Code, Cursor, Windsurf, Claude Desktop, Claude Code, etc.)

## Getting Started

### Installation

```bash
pip install terminalcp
```

Or use directly with uvx (no installation needed):

```bash
uvx terminalcp --mcp
```

### MCP Client Configuration

**Standard config** works in most tools:

```json
{
  "mcpServers": {
    "terminalcp": {
      "command": "uvx",
      "args": ["terminalcp", "--mcp"]
    }
  }
}
```

<details>
<summary>Claude Code</summary>

Use the Claude Code CLI to add the terminalcp server:

```bash
claude mcp add -s user terminalcp uvx terminalcp --mcp
```
</details>

<details>
<summary>Claude Desktop</summary>

Follow the MCP install [guide](https://modelcontextprotocol.io/quickstart/user), use the standard config above.
</details>

<details>
<summary>Cursor</summary>

Go to `Cursor Settings` -> `MCP` -> `Add new MCP Server`. Name it "terminalcp", use `command` type with the command `uvx terminalcp --mcp`.
</details>

<details>
<summary>VS Code</summary>

Follow the MCP install [guide](https://code.visualstudio.com/docs/copilot/chat/mcp-servers#_add-an-mcp-server), use the standard config above.
</details>

<details>
<summary>Installed via pip</summary>

If you installed globally with `pip install terminalcp`:

```json
{
  "mcpServers": {
    "terminalcp": {
      "command": "terminalcp",
      "args": ["--mcp"]
    }
  }
}
```
</details>

## MCP Usage Examples

The following examples show the JSON arguments passed to the single `terminalcp` tool exposed by the MCP server. The MCP server returns plain text responses to minimize token usage.

### Starting and Managing Processes

```json
// Start with auto-generated ID
{"action": "start", "command": "python3 -i"}
// Returns: "proc-3465b9b687af"

// Start with custom name (becomes the ID)
{"action": "start", "command": "npm run dev", "name": "dev-server"}
// Returns: "dev-server"

// Start in specific directory
{"action": "start", "command": "python3 script.py", "cwd": "/path/to/project", "name": "analyzer"}
// Returns: "analyzer"
```

### Interacting with Running Sessions

```json
// Send text with Enter key (\r)
{"action": "stdin", "id": "dev-server", "data": "npm test\r"}
// Returns: ""

// Send arrow keys (\u001b[D = Left arrow)
{"action": "stdin", "id": "editor", "data": "echo hello\u001b[D\u001b[D\u001b[D\u001b[Dhi \r"}

// Send control sequences
{"action": "stdin", "id": "process", "data": "\u0003"}  // Ctrl+C
{"action": "stdin", "id": "shell", "data": "\u0004"}     // Ctrl+D (EOF)

// Get terminal output (rendered screen)
{"action": "stdout", "id": "dev-server"}
// Returns: Full terminal screen with colors and formatting

// Get last N lines only
{"action": "stdout", "id": "dev-server", "lines": 50}
```

### Monitoring Long-Running Processes

```json
// Get all output as raw stream (ANSI codes stripped)
{"action": "stream", "id": "dev-server"}

// Get only new output since last check
{"action": "stream", "id": "dev-server", "since_last": true}

// Keep ANSI color codes
{"action": "stream", "id": "dev-server", "since_last": true, "strip_ansi": false}
```

### Process Management

```json
// List all sessions
{"action": "list"}
// Returns: "dev-server running /Users/you/project npm run dev\nanalyzer stopped /path python3 script.py"

// Stop specific process
{"action": "stop", "id": "dev-server"}
// Returns: "stopped dev-server"

// Stop ALL processes
{"action": "stop"}
// Returns: "stopped 3 processes"

// Kill the terminal server
{"action": "kill-server"}
// Returns: "shutting down"
```

### Interactive AI Agents Example

```json
// Start Claude with a name
{"action": "start", "command": "/path/to/claude --dangerously-skip-permissions", "name": "claude"}

// Send a prompt
{"action": "stdin", "id": "claude", "data": "Write a test for main.py\r"}

// Get the response
{"action": "stdout", "id": "claude"}

// Clean up
{"action": "stop", "id": "claude"}
```

### Debugging with LLDB

```json
{"action": "start", "command": "lldb ./myapp", "name": "debugger"}
{"action": "stdin", "id": "debugger", "data": "break main\r"}
{"action": "stdin", "id": "debugger", "data": "run\r"}
{"action": "stdout", "id": "debugger"}
{"action": "stdin", "id": "debugger", "data": "bt\r"}
{"action": "stdout", "id": "debugger"}
```

### Build Process Monitoring

```json
{"action": "start", "command": "npm run build", "name": "build"}
// Monitor progress
{"action": "stream", "id": "build", "since_last": true}
// ... wait ...
{"action": "stream", "id": "build", "since_last": true}  // Only new output
```

## CLI Usage

terminalcp can also be used as a standalone CLI tool:

```bash
# List all active sessions
terminalcp ls

# Start a new session with a custom name
terminalcp start my-app "npm run dev"

# Attach to a session interactively (Ctrl+B to detach)
terminalcp attach my-app

# Get output from a session
terminalcp stdout my-app
terminalcp stdout my-app 50  # Last 50 lines

# Send input to a session (use :: prefix for special keys)
terminalcp stdin my-app "echo hello" ::Enter
terminalcp stdin my-app "echo test" ::Left ::Left ::Left "hi " ::Enter
terminalcp stdin my-app ::C-c  # Send Ctrl+C

# Monitor logs
terminalcp stream my-app --since-last
terminalcp stream my-app --with-ansi  # Keep ANSI codes

# Resize terminal
terminalcp resize my-app 120 40

# Get terminal size
terminalcp term-size my-app

# Stop sessions
terminalcp stop my-app
terminalcp stop  # Stop all

# Maintenance
terminalcp version
terminalcp kill-server
```

## Zsh Completion

Auto-install (recommended):

```bash
terminalcp completion
```

Manual install:

```bash
mkdir -p ~/.zsh/completions
cp /path/to/terminalcp/terminalcp/completion/scripts/_terminalcp.zsh ~/.zsh/completions/_terminalcp
```

Enable completions in `~/.zshrc`:

```bash
fpath=(~/.zsh/completions $fpath)
autoload -Uz compinit && compinit
compdef _terminalcp terminalcp
```

## Attaching to Sessions

You can attach to any session from your terminal to watch or interact with AI-spawned processes:

1. **AI spawns a process with a name**:
```json
{"action": "start", "command": "python3 -i", "name": "python-debug"}
```

2. **Attach from your terminal**:
```bash
terminalcp attach python-debug
```

3. **Interact directly**:
- Type commands as normal
- Terminal resizing is automatically synchronized
- Press **Ctrl+B** to detach (session continues running)
- Multiple users can attach to the same session simultaneously

## Important Usage Notes

- **MCP Escape Sequences**: Send special keys using escape sequences: `\r` (Enter), `\u001b[A` (Up), `\u0003` (Ctrl+C)
- **CLI Special Keys**: Use `::` prefix: `::Enter`, `::Left`, `::C-c`, `::M-x`, `::F1`-`::F12`
- **Aliases don't work**: Commands run via `bash -c`, so use absolute paths or commands in PATH
- **Process persistence**: Sessions persist across MCP server restarts — manually stop them when done
- **Named sessions**: Use the `name` parameter when starting to create human-readable session IDs

### Common Escape Sequences (for MCP)

```
// Basic keys
Enter: "\r"          Tab: "\t"         Escape: "\u001b"      Backspace: "\u007f"

// Control keys
Ctrl+C: "\u0003"     Ctrl+D: "\u0004"  Ctrl+Z: "\u001a"      Ctrl+L: "\u000c"

// Arrow keys
Up: "\u001b[A"       Down: "\u001b[B"   Right: "\u001b[C"     Left: "\u001b[D"

// Navigation
Home: "\u001b[H"     End: "\u001b[F"    PageUp: "\u001b[5~"   PageDown: "\u001b[6~"

// Function keys
F1: "\u001bOP"       F2: "\u001bOQ"     F3: "\u001bOR"        F4: "\u001bOS"

// Meta/Alt (ESC + character)
Alt+x: "\u001bx"     Alt+b: "\u001bb"   Alt+f: "\u001bf"
```

## Programmatic Usage with TerminalManager

The `TerminalManager` class provides a programmatic API for driving TUI applications, useful for automation, testing, or building higher-level abstractions.

### Basic Usage

```python
import asyncio
from terminalcp import TerminalManager, build_input

async def main():
    manager = TerminalManager()

    # Start a process
    session_id = await manager.start('python3 -i', {'name': 'python-repl'})

    # Send input
    await manager.send_input(session_id, '2 + 2\r')

    # Wait for output to settle
    await asyncio.sleep(0.5)

    # Get rendered terminal screen
    output = await manager.get_output(session_id)
    print(output)

    # Get raw stream output
    stream = await manager.get_stream(session_id, since_last=True)
    print(stream)

    # Send special keys using build_input helper
    await manager.send_input(session_id, build_input('Up', 'Enter'))

    # Clean up
    await manager.stop(session_id)

asyncio.run(main())
```

### Advanced TUI Interaction

```python
import asyncio
from terminalcp import TerminalManager, build_input

async def drive_debugger():
    manager = TerminalManager()

    # Start LLDB
    debug_id = await manager.start('lldb ./myapp')
    await manager.send_input(debug_id, 'break main\r')
    await manager.send_input(debug_id, 'run\r')

    await asyncio.sleep(1)

    # Get debugger output
    output = await manager.get_output(debug_id)
    print(output)

    # Navigate with special keys
    await manager.send_input(debug_id, build_input('Up', 'Up', 'Enter'))

    # Monitor streaming output
    logs = await manager.get_stream(debug_id, since_last=True)
    print(logs)

    await manager.stop(debug_id)

asyncio.run(drive_debugger())
```

### Testing TUI Applications

```python
import asyncio
import pytest
from terminalcp import TerminalManager

async def wait_for_output(manager, session_id, pattern, timeout=5.0):
    """Wait until terminal output contains the expected pattern."""
    elapsed = 0.0
    while elapsed < timeout:
        output = await manager.get_output(session_id)
        if pattern in output:
            return output
        await asyncio.sleep(0.1)
        elapsed += 0.1
    raise TimeoutError(f"Timeout waiting for: {pattern}")

@pytest.mark.asyncio
async def test_python_repl():
    manager = TerminalManager()
    session_id = await manager.start('python3 -i')

    try:
        await wait_for_output(manager, session_id, '>>>')
        await manager.send_input(session_id, '2 + 2\r')
        output = await wait_for_output(manager, session_id, '4')
        assert '4' in output
    finally:
        await manager.stop(session_id)

@pytest.mark.asyncio
async def test_vim_navigation():
    manager = TerminalManager()
    session_id = await manager.start('vim')

    try:
        await manager.send_input(session_id, 'iHello\x1b')  # Insert + ESC
        await asyncio.sleep(0.3)
        output = await manager.get_output(session_id)
        assert 'Hello' in output
    finally:
        await manager.stop(session_id)
```

## How it works

terminalcp uses a layered architecture for flexibility and persistence:

### Architecture Layers

1. **TerminalManager** — Core library that manages PTY sessions
   - Creates pseudo-TTY processes via Python's `pty` module
   - Maintains virtual terminals using [pyte](https://github.com/selectel/pyte)
   - Handles input/output, ANSI sequences, and terminal emulation
   - Provides the programmatic API for all terminal operations

2. **TerminalServer** — Persistent background daemon
   - Auto-spawns when needed by CLI or MCP
   - Listens on Unix domain socket at `~/.terminalcp/server.sock`
   - Manages all active terminal sessions across clients
   - Sessions persist even when clients disconnect

3. **TerminalClient** — Communication layer
   - Used by both CLI and MCP to talk to TerminalServer
   - Sends commands over Unix socket
   - Handles connection management, retries, and version checking

4. **User Interfaces**
   - **MCP Server**: Exposes `terminalcp` tool via [FastMCP](https://github.com/modelcontextprotocol/python-sdk), uses TerminalClient to communicate with TerminalServer
   - **CLI**: Command-line interface, uses TerminalClient for communication
   - Both interfaces provide the same functionality

### MCP Tool: `terminalcp`

The MCP server exposes a single tool called `terminalcp` that accepts JSON commands with different action types:

| Action | Parameters | Returns |
|--------|-----------|---------|
| `start` | `command`, `cwd?`, `name?` | Session ID string |
| `stop` | `id?` (omit to stop all) | Confirmation message |
| `stdout` | `id`, `lines?` | Rendered terminal screen |
| `stream` | `id`, `since_last?`, `strip_ansi?` | Raw output text |
| `stdin` | `id`, `data` | Empty string |
| `list` | — | Newline-separated session list |
| `term-size` | `id` | "rows cols scrollback_lines" |
| `kill-server` | — | "shutting down" |

## Development

```bash
# Clone and install in editable mode
git clone <repo>
cd terminalcp
pip install -e .

# Run as MCP server
terminalcp --mcp

# Run as terminal server daemon
terminalcp --server

# Local development with uvx
uvx --from . terminalcp --mcp
```

## License

MIT
