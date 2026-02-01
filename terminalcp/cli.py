from __future__ import annotations

import asyncio
import signal
import os
import sys
from importlib.metadata import PackageNotFoundError, version

from .attach_client import AttachClient
from .key_parser import parse_key_input
from .mcp_server import run_mcp_server
from .terminal_client import TerminalClient
from .terminal_server import TerminalServer

def get_client_version() -> str:
    try:
        return version("terminalcp")
    except PackageNotFoundError:
        return "0.0.0"


def print_help() -> None:
    print(
        """terminalcp - Terminal Control Protocol
A centralized terminal session manager with MCP server support

USAGE:
  terminalcp --mcp                       Start as MCP server on stdio
  terminalcp --server                    Start the terminal server daemon
  terminalcp <command> [options]         Run a CLI command

COMMANDS:
  list, ls                               List all active sessions
  start <id> <command>                   Start a new named session
  stop [id]                              Stop session(s) (all if no id given)
  attach <id>                            Attach to a session interactively
  stdout <id> [lines]                    Get terminal output (rendered view)
  stream <id> [opts]                     Get raw output stream
  stdin <id> <data>                      Send input to a session
  resize <id> <cols> <rows>              Resize terminal dimensions
  term-size <id>                         Get terminal size
  completion [--shell TYPE]              Install shell completion (bash/zsh/fish)
  version                                Show client and server versions
  kill-server                            Shutdown the terminal server

EXAMPLES:
  # Start as MCP server
  terminalcp --mcp

  # Start a development server
  terminalcp start dev-server "npm run dev"

  # Start an interactive Python session
  terminalcp start python "python3 -i"
  terminalcp stdin python "print('Hello')\r"
  terminalcp stdout python

  # Debug with lldb
  terminalcp start debug "lldb ./myapp"
  terminalcp stdin debug "b main\r"
  terminalcp stdin debug "run\r"
  terminalcp attach debug  # Interactive debugging

  # Monitor build output
  terminalcp start build "npm run build"
  terminalcp stream build --since-last

  # Attach to interact with a session
  terminalcp attach python
  # Press Ctrl+B to detach

OPTIONS:
  --mcp                                  Run as MCP server on stdio
  --server                               Run as terminal server daemon
  --since-last                           Only show new output (stream)
  --with-ansi                            Keep ANSI codes (stream)

CONFIGURATION:
  Add to your MCP client configuration:
  {
    "mcpServers": {
      "terminalcp": {
        "command": "terminalcp",
        "args": ["--mcp"]
      }
    }
  }

  Or using uvx:
  {
    "mcpServers": {
      "terminalcp": {
        "command": "uvx",
        "args": ["terminalcp", "--mcp"]
      }
    }
  }

For more information: https://github.com/badlogic/terminalcp"""
    )


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print_help()
        return

    if args[0] == "--mcp":
        run_mcp_server()
        return

    if args[0] == "--server":
        async def _run_server() -> None:
            server = TerminalServer()
            loop = asyncio.get_running_loop()
            for sig in ("SIGINT", "SIGTERM", "SIGQUIT"):
                if hasattr(signal, sig):
                    loop.add_signal_handler(getattr(signal, sig), lambda: asyncio.create_task(server.shutdown()))
            await server.run_forever()

        asyncio.run(_run_server())
        return

    command = args[0]

    if command in {"ls", "list"}:
        async def _list() -> None:
            client = TerminalClient()
            try:
                response = await client.request({"action": "list"})
            except Exception as exc:
                if str(exc) == "No server running":
                    print("No active sessions")
                    return
                print(str(exc), file=sys.stderr)
                raise SystemExit(1)

            lines = [line for line in str(response).split("\n") if line.strip()]
            if not lines:
                print("No active sessions")
                return
            for line in lines:
                parts = line.split(" ")
                session_id = parts[0]
                status = parts[1] if len(parts) > 1 else "unknown"
                cwd = parts[2] if len(parts) > 2 else ""
                command_text = " ".join(parts[3:]) if len(parts) > 3 else ""
                print(f"  {session_id}")
                print(f"    Status: {status}")
                print(f"    CWD: {cwd}")
                print(f"    Command: {command_text}")
                print()

        asyncio.run(_list())
        return

    if command == "start":
        if len(args) < 3:
            print("Usage: terminalcp start <session-id> <command> [args...]", file=sys.stderr)
            raise SystemExit(1)
        session_id = args[1]
        command_text = " ".join(args[2:])

        async def _start() -> None:
            client = TerminalClient()
            try:
                result = await client.request({"action": "start", "command": command_text, "name": session_id})
            except Exception as exc:
                print(f"Failed to start session: {exc}", file=sys.stderr)
                raise SystemExit(1)
            print(f"Started session: {result}")

        asyncio.run(_start())
        return

    if command == "stop":
        session_id = args[1] if len(args) > 1 else None

        async def _stop() -> None:
            client = TerminalClient()
            try:
                result = await client.request({"action": "stop", "id": session_id})
            except Exception as exc:
                print(f"Failed to stop session: {exc}", file=sys.stderr)
                raise SystemExit(1)
            print(result)

        asyncio.run(_stop())
        return

    if command == "stdout":
        if len(args) < 2:
            print("Usage: terminalcp stdout <id> [lines]", file=sys.stderr)
            raise SystemExit(1)
        session_id = args[1]
        lines = int(args[2]) if len(args) > 2 else None

        async def _stdout() -> None:
            client = TerminalClient()
            try:
                output = await client.request({"action": "stdout", "id": session_id, "lines": lines})
            except Exception as exc:
                print(f"Failed to get stdout: {exc}", file=sys.stderr)
                raise SystemExit(1)
            sys.stdout.write(output)

        asyncio.run(_stdout())
        return

    if command == "stream":
        if len(args) < 2:
            print("Usage: terminalcp stream <id> [--since-last] [--with-ansi]", file=sys.stderr)
            raise SystemExit(1)
        session_id = args[1]
        since_last = "--since-last" in args
        strip_ansi = "--with-ansi" not in args

        async def _stream() -> None:
            client = TerminalClient()
            try:
                output = await client.request(
                    {"action": "stream", "id": session_id, "since_last": since_last, "strip_ansi": strip_ansi}
                )
            except Exception as exc:
                print(f"Failed to get stream: {exc}", file=sys.stderr)
                raise SystemExit(1)
            sys.stdout.write(output)

        asyncio.run(_stream())
        return

    if command == "stdin":
        if len(args) < 3:
            print("Usage: terminalcp stdin <id> <text> [text] ...", file=sys.stderr)
            print("\nUse :: prefix for special keys:", file=sys.stderr)
            print('  terminalcp stdin session "hello world" ::Enter', file=sys.stderr)
            print("  terminalcp stdin session hello ::Space world ::Enter", file=sys.stderr)
            print('  terminalcp stdin session "echo test" ::Left ::Left ::Left "hi " ::Enter', file=sys.stderr)
            print('  terminalcp stdin session ::C-c "echo done" ::Enter', file=sys.stderr)
            print("\nSpecial keys: ::Up, ::Down, ::Left, ::Right, ::Enter, ::Tab, ::Space", file=sys.stderr)
            print("              ::Home, ::End, ::PageUp, ::PageDown, ::Insert, ::Delete", file=sys.stderr)
            print("              ::F1-F12, ::BSpace, ::C-<key>, ::M-<key>, ::^<key>", file=sys.stderr)
            raise SystemExit(1)
        session_id = args[1]
        data_args = args[2:]
        data = parse_key_input(data_args)

        async def _stdin() -> None:
            client = TerminalClient()
            try:
                await client.request({"action": "stdin", "id": session_id, "data": data})
            except Exception as exc:
                print(f"Failed to send stdin: {exc}", file=sys.stderr)
                raise SystemExit(1)

        asyncio.run(_stdin())
        return

    if command == "term-size":
        if len(args) < 2:
            print("Usage: terminalcp term-size <id>", file=sys.stderr)
            raise SystemExit(1)
        session_id = args[1]

        async def _term_size() -> None:
            client = TerminalClient()
            try:
                result = await client.request({"action": "term-size", "id": session_id})
            except Exception as exc:
                print(f"Failed to get terminal size: {exc}", file=sys.stderr)
                raise SystemExit(1)
            print(result)

        asyncio.run(_term_size())
        return

    if command == "resize":
        if len(args) < 4:
            print("Usage: terminalcp resize <id> <cols> <rows>", file=sys.stderr)
            raise SystemExit(1)
        session_id = args[1]
        cols = int(args[2])
        rows = int(args[3])

        async def _resize() -> None:
            client = TerminalClient()
            try:
                await client.request({"action": "resize", "id": session_id, "cols": cols, "rows": rows})
            except Exception as exc:
                print(f"Failed to resize terminal: {exc}", file=sys.stderr)
                raise SystemExit(1)
            print("Terminal resized")

        asyncio.run(_resize())
        return

    if command == "attach":
        if len(args) < 2:
            print("Usage: terminalcp attach <id>", file=sys.stderr)
            raise SystemExit(1)
        session_id = args[1]

        async def _attach() -> None:
            client = AttachClient()
            await client.attach(session_id)

        asyncio.run(_attach())
        return

    if command == "completion":
        from .completion import install_completion

        shell_override = None
        for i, arg in enumerate(args[1:], 1):
            if arg == "--shell" and i + 1 < len(args):
                shell_override = args[i + 1]
            elif arg.startswith("--shell="):
                shell_override = arg.split("=", 1)[1]
        install_completion(shell=shell_override)
        return

    if command == "version":
        async def _version() -> None:
            client_version = get_client_version()
            client = TerminalClient()
            try:
                server_version = await client.request({"action": "version"})
                print(f"Server version: {server_version}")
                print(f"Client version: {client_version}")
            except Exception as exc:
                print(f"Failed to get server version: {exc}", file=sys.stderr)
                print(f"Client version: {client_version}")
                raise SystemExit(1)

        asyncio.run(_version())
        return

    if command == "kill-server":
        socket_path = os.path.join(os.path.expanduser("~"), ".terminalcp", "server.sock")
        if not os.path.exists(socket_path):
            print("No server running", file=sys.stderr)
            raise SystemExit(1)

        async def _kill() -> None:
            client = TerminalClient()
            try:
                await client.request({"action": "kill-server"})
            except Exception as exc:
                print(f"Failed to kill server: {exc}", file=sys.stderr)
                raise SystemExit(1)
            print("Server killed")

        asyncio.run(_kill())
        return

    print(f"Unknown command: {command}", file=sys.stderr)
    print("Run 'terminalcp' without arguments to see help", file=sys.stderr)
    raise SystemExit(1)
