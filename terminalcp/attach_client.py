from __future__ import annotations

import asyncio
import json
import os
import signal
import sys
import termios
import tty
from typing import Any, Dict, Optional

from .messages import create_request


class AttachClient:
    def __init__(self) -> None:
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.attached_session: Optional[str] = None
        self._stdin_fd = sys.stdin.fileno()
        self._stdout = sys.stdout
        self._orig_term_settings: Optional[list[Any]] = None

    async def attach(self, session_id: str) -> None:
        print(f"Attaching to session {session_id}...", file=sys.stderr)
        print("Press Ctrl+B to detach", file=sys.stderr)
        print("", file=sys.stderr)

        self.reader, self.writer = await asyncio.open_unix_connection(
            os.path.join(os.path.expanduser("~"), ".terminalcp", "server.sock")
        )
        self.attached_session = session_id

        attach_response = await self._request_attach(session_id)
        self._setup_terminal()
        self._reset_terminal()

        raw_output = attach_response.get("rawOutput")
        if raw_output:
            self._stdout.write(raw_output)
            self._stdout.flush()

        loop = asyncio.get_running_loop()
        loop.add_reader(self._stdin_fd, self._handle_stdin)
        try:
            loop.add_signal_handler(signal.SIGWINCH, lambda: asyncio.create_task(self._send_resize()))
        except NotImplementedError:
            pass

        try:
            await self._read_loop()
        finally:
            self._cleanup()

    async def _request_attach(self, session_id: str) -> Dict[str, Any]:
        if not self.writer or not self.reader:
            raise RuntimeError("Not connected")
        request = create_request({"action": "attach", "id": session_id})
        request_id = request["id"]
        self.writer.write((json.dumps(request) + "\n").encode("utf-8"))
        await self.writer.drain()

        try:
            while True:
                line = await asyncio.wait_for(self.reader.readline(), timeout=5)
                if not line:
                    raise RuntimeError("Session closed")
                message = json.loads(line.decode("utf-8", errors="replace"))
                if message.get("type") == "response" and message.get("id") == request_id:
                    if message.get("error"):
                        raise RuntimeError(message.get("error"))
                    result = message.get("result")
                    if not isinstance(result, dict):
                        raise RuntimeError("Invalid response format")
                    return result
        except asyncio.TimeoutError as exc:
            raise RuntimeError(f"Request timeout - no response for request {request_id}") from exc

    async def _read_loop(self) -> None:
        assert self.reader is not None
        while not self.reader.at_eof():
            line = await self.reader.readline()
            if not line:
                break
            try:
                message = json.loads(line.decode("utf-8", errors="replace"))
            except json.JSONDecodeError:
                continue
            self._handle_message(message)

    def _handle_message(self, message: Dict[str, Any]) -> None:
        if message.get("type") != "event":
            return
        if message.get("event") != "output":
            return
        if message.get("sessionId") != self.attached_session:
            return
        data = message.get("data", "")
        if data:
            self._stdout.write(data)
            self._stdout.flush()

    def _handle_stdin(self) -> None:
        if not self.writer or not self.attached_session:
            return
        data = os.read(self._stdin_fd, 1024)
        if not data:
            return
        if data[0] == 0x02:
            asyncio.create_task(self._detach())
            return
        text = data.decode("utf-8", errors="replace")
        message = create_request({"action": "stdin", "id": self.attached_session, "data": text})
        self.writer.write((json.dumps(message) + "\n").encode("utf-8"))

    async def _send_resize(self) -> None:
        if not self.writer or not self.attached_session:
            return
        cols, rows = self._get_terminal_size()
        message = create_request({
            "action": "resize",
            "id": self.attached_session,
            "cols": cols,
            "rows": rows,
        })
        self.writer.write((json.dumps(message) + "\n").encode("utf-8"))
        await self.writer.drain()

    async def _detach(self) -> None:
        print("\n[Detaching...]", file=sys.stderr)
        if self.writer and self.attached_session:
            message = create_request({"action": "detach", "id": self.attached_session})
            self.writer.write((json.dumps(message) + "\n").encode("utf-8"))
            await self.writer.drain()
            self.writer.close()
        self._cleanup()

    def _setup_terminal(self) -> None:
        if not sys.stdin.isatty():
            print("Not running in a TTY", file=sys.stderr)
            raise SystemExit(1)
        self._orig_term_settings = termios.tcgetattr(self._stdin_fd)
        tty.setraw(self._stdin_fd)
        asyncio.create_task(self._send_resize())

    def _reset_terminal(self) -> None:
        self._stdout.write(
            "\x1b[?1000l\x1b[?1002l\x1b[?1003l\x1b[?1006l"
            "\x1b[?47l\x1b[?1049l\x1b[?25h\x1b[0m\x1bc"
        )
        self._stdout.flush()

    def _cleanup(self) -> None:
        try:
            loop = asyncio.get_running_loop()
            loop.remove_reader(self._stdin_fd)
        except Exception:
            pass

        if self._orig_term_settings:
            try:
                termios.tcsetattr(self._stdin_fd, termios.TCSADRAIN, self._orig_term_settings)
            except Exception:
                pass
            self._orig_term_settings = None

        self._reset_terminal()

    def _get_terminal_size(self) -> tuple[int, int]:
        try:
            size = os.get_terminal_size(sys.stdout.fileno())
            return size.columns, size.lines
        except OSError:
            return 80, 24
