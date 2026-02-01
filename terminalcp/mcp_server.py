from __future__ import annotations

from typing import Any, Dict

from mcp.server.fastmcp import FastMCP

from .terminal_client import TerminalClient


def run_mcp_server() -> None:
    client = TerminalClient()

    mcp = FastMCP("terminalcp")

    @mcp.tool()
    async def terminalcp(args: Dict[str, Any]) -> str:
        """
        Control background processes with virtual terminals. IMPORTANT: Always clean up processes with "stop" action when done.

        Examples:
          Start dev server: {"action": "start", "command": "npm run dev", "cwd": "/path/to/project"}
          Send text with Enter: {"action": "stdin", "id": "proc-123", "data": "npm test\\r"}
          Send arrow keys: {"action": "stdin", "id": "proc-123", "data": "echo hello\\u001b[D\\u001b[D\\u001b[Dhi \\r"}
          Send Ctrl+C: {"action": "stdin", "id": "proc-123", "data": "\\u0003"}
          Stop process: {"action": "stop", "id": "proc-abc123"}
          Stop all processes: {"action": "stop"}

          Get terminal screen: {"action": "stdout", "id": "proc-123"}  # Current view + scrollback
          Get last 50 lines: {"action": "stdout", "id": "proc-123", "lines": 50}
          Get all output ever: {"action": "stream", "id": "proc-123"}  # From process start
          Get new output only: {"action": "stream", "id": "proc-123", "since_last": true}  # Since last stream call

        Output modes:
          stdout: Terminal emulator output - returns the rendered screen as user would see it.
                  Limited to 10K lines scrollback. Best for: interactive tools, TUIs, REPLs, debuggers.

          stream: Raw process output - returns all text the process has written to stdout/stderr.
                  Strips ANSI codes by default (set strip_ansi: false to keep). No limit on history.
                  With since_last: true, returns only new output since last stream call on this process.
                  Best for: build logs, test output, monitoring long-running processes.

        Common escape sequences for stdin:
          Enter: \\r or \\u000d
          Tab: \\t or \\u0009
          Escape: \\u001b
          Backspace: \\u007f
          Ctrl+C: \\u0003
          Ctrl+D: \\u0004
          Ctrl+Z: \\u001a

          Arrow keys: Up=\\u001b[A Down=\\u001b[B Right=\\u001b[C Left=\\u001b[D
          Navigation: Home=\\u001b[H End=\\u001b[F PageUp=\\u001b[5~ PageDown=\\u001b[6~
          Delete: \\u001b[3~ Insert: \\u001b[2~
          Function keys: F1=\\u001bOP F2=\\u001bOQ F3=\\u001bOR F4=\\u001bOS
          Meta/Alt: Alt+x=\\u001bx (ESC followed by character)

        Interactive examples:
          Vim: stdin "vim test.txt\\r" -> stdin "iHello\\u001b:wq\\r" -> stdout
          Python: start "python3 -i" -> stdin "2+2\\r" -> stdout
          Build monitoring: start "npm run build" -> stream (since_last: true) -> repeat
          Interrupt: stdin "sleep 10\\r" -> stdin "\\u0003" (Ctrl+C)

        Note: Commands run via bash -c. Use absolute paths, not aliases.
        """

        if not isinstance(args, dict):
            raise ValueError("Invalid arguments: expected JSON object")

        action = args.get("action")
        valid_actions = {"start", "stop", "stdout", "stdin", "list", "stream", "term-size", "kill-server"}
        if action not in valid_actions:
            raise ValueError(f"Unknown action: {action}. Valid actions: {', '.join(sorted(valid_actions))}")

        try:
            result = await client.request(args)
            return result or ""
        except Exception as exc:
            message = str(exc)
            if message in {"No server running", "Request timeout"}:
                action = args.get("action")
                if action == "list":
                    return "No active sessions"
                if action == "start":
                    raise
                return (
                    "Error: No terminal server running. Use \"list\" to check status or start a process to auto-start the server."
                )
            raise

    mcp.run()
