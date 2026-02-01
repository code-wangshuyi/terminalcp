from __future__ import annotations

import asyncio
import json
import os
import sys
import subprocess
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Dict, Optional

from .terminal_manager import TerminalManager


@dataclass
class ClientConnection:
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter


def get_package_version() -> str:
    try:
        return version("terminalcp")
    except PackageNotFoundError:
        return "0.0.0"


class TerminalServer:
    def __init__(self) -> None:
        self.process_manager = TerminalManager()
        self.server: Optional[asyncio.AbstractServer] = None
        self.clients: Dict[str, ClientConnection] = {}
        self.session_subscribers: Dict[str, set[str]] = {}
        self.client_counter = 0
        self.server_socket_path = os.path.join(os.path.expanduser("~"), ".terminalcp", "server.sock")

        socket_dir = Path(self.server_socket_path).parent
        socket_dir.mkdir(parents=True, exist_ok=True)

    async def start(self) -> None:
        if os.path.exists(self.server_socket_path):
            try:
                os.unlink(self.server_socket_path)
            except OSError:
                pass

        self.server = await asyncio.start_unix_server(self._handle_client, path=self.server_socket_path)
        os.chmod(self.server_socket_path, 0o600)
        print(f"Terminal server listening at {self.server_socket_path}", file=sys.stderr)

    async def run_forever(self) -> None:
        await self.start()
        if not self.server:
            return
        async with self.server:
            await self.server.serve_forever()

    async def shutdown(self) -> None:
        print("Shutting down terminal server...", file=sys.stderr)
        await self.process_manager.stop_all()

        for conn in self.clients.values():
            try:
                conn.writer.close()
            except Exception:
                pass
        self.clients.clear()

        if self.server:
            self.server.close()
            await self.server.wait_closed()

        if os.path.exists(self.server_socket_path):
            try:
                os.unlink(self.server_socket_path)
            except OSError:
                pass

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self.client_counter += 1
        client_id = f"client-{self.client_counter}"
        self.clients[client_id] = ClientConnection(reader=reader, writer=writer)

        try:
            while not reader.at_eof():
                line = await reader.readline()
                if not line:
                    break
                line_str = line.decode("utf-8", errors="replace").strip()
                if not line_str:
                    continue
                try:
                    message = json.loads(line_str)
                except json.JSONDecodeError:
                    await self._send_error(client_id, "invalid-request", "Invalid JSON")
                    continue
                await self._handle_message(client_id, message)
        finally:
            self.clients.pop(client_id, None)
            for subscribers in self.session_subscribers.values():
                subscribers.discard(client_id)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _handle_message(self, client_id: str, message: Dict[str, Any]) -> None:
        request_id = message.get("id")
        args = message.get("args") or {}
        action = args.get("action")

        if not request_id or not action:
            await self._send_error(client_id, request_id or "unknown", "Missing required fields")
            return

        try:
            result: Any = ""

            if action == "start":
                command = args.get("command")
                cwd = args.get("cwd")
                name = args.get("name")
                if not command:
                    raise RuntimeError("Missing required field: command")
                session_id = await self.process_manager.start(command, {"cwd": cwd, "name": name})
                self.process_manager.on_output(session_id, self._make_output_handler())

                self.session_subscribers.setdefault(session_id, set()).add(client_id)
                result = session_id

            elif action == "stop":
                session_id = args.get("id")
                if not session_id:
                    processes = self.process_manager.list_processes()
                    count = 0
                    for proc in processes:
                        self.process_manager.off_output(proc["id"])
                        await self.process_manager.stop(proc["id"])
                        count += 1
                    result = f"stopped {count} processes"
                else:
                    self.process_manager.off_output(session_id)
                    await self.process_manager.stop(session_id)
                    result = f"stopped {session_id}"

            elif action == "stdin":
                session_id = args.get("id")
                data = args.get("data")
                if not session_id or data is None:
                    raise RuntimeError("Missing required fields: id, data")
                await self.process_manager.send_input(session_id, data)
                result = ""

            elif action == "stdout":
                session_id = args.get("id")
                if not session_id:
                    raise RuntimeError("Missing required field: id")
                lines = args.get("lines")
                lines_int = int(lines) if lines is not None else None
                result = await self.process_manager.get_output(session_id, lines=lines_int)

            elif action == "stream":
                session_id = args.get("id")
                if not session_id:
                    raise RuntimeError("Missing required field: id")
                since_last = bool(args.get("since_last"))
                strip_ansi = args.get("strip_ansi")
                result = await self.process_manager.get_stream(
                    session_id, since_last=since_last, strip_ansi_codes=strip_ansi
                )

            elif action == "list":
                processes = self.process_manager.list_processes()
                lines = [
                    f"{proc['id']} {'running' if proc['running'] else 'stopped'} {proc['cwd']} {proc['command']}"
                    for proc in processes
                ]
                result = "\n".join(lines)

            elif action == "term-size":
                session_id = args.get("id")
                if not session_id:
                    raise RuntimeError("Missing required field: id")
                size = self.process_manager.get_terminal_size(session_id)
                result = f"{size['rows']} {size['cols']} {size['scrollback_lines']}"

            elif action == "attach":
                session_id = args.get("id")
                if not session_id:
                    raise RuntimeError("Missing required field: id")
                proc = self.process_manager.get_process(session_id)
                if not proc:
                    raise RuntimeError(f"Process not found: {session_id}")
                self.session_subscribers.setdefault(session_id, set()).add(client_id)
                result = {"cols": proc.cols, "rows": proc.rows, "rawOutput": proc.raw_output}

            elif action == "resize":
                session_id = args.get("id")
                cols = args.get("cols")
                rows = args.get("rows")
                if not session_id:
                    raise RuntimeError("Missing required field: id")
                if cols is None or rows is None:
                    raise RuntimeError("Missing required fields: cols, rows")
                self.process_manager.resize_terminal(session_id, int(cols), int(rows))
                self._broadcast_event(
                    {
                        "type": "event",
                        "event": "resize",
                        "sessionId": session_id,
                        "cols": cols,
                        "rows": rows,
                    }
                )
                result = ""

            elif action == "detach":
                session_id = args.get("id")
                if not session_id:
                    raise RuntimeError("Missing required field: id")
                subscribers = self.session_subscribers.get(session_id)
                if subscribers:
                    subscribers.discard(client_id)
                result = "detached"

            elif action == "kill-server":
                result = "shutting down"
                await self._send_response(client_id, request_id, result)
                await self.shutdown()
                return

            elif action == "version":
                result = get_package_version()

            else:
                raise RuntimeError(f"Unknown action: {action}")

            await self._send_response(client_id, request_id, result)
        except Exception as exc:
            await self._send_error(client_id, request_id, str(exc))

    def _make_output_handler(self) -> Any:
        def handler(session_id: str, data: str) -> None:
            self._broadcast_event(
                {
                    "type": "event",
                    "event": "output",
                    "sessionId": session_id,
                    "data": data,
                }
            )

        return handler

    def _broadcast_event(self, event: Dict[str, Any]) -> None:
        session_id = event.get("sessionId")
        subscribers = self.session_subscribers.get(session_id)
        if not subscribers:
            return
        message = json.dumps(event) + "\n"
        for client_id in list(subscribers):
            conn = self.clients.get(client_id)
            if not conn:
                continue
            try:
                conn.writer.write(message.encode("utf-8"))
                asyncio.create_task(conn.writer.drain())
            except Exception:
                continue

    async def _send_response(self, client_id: str, request_id: str, result: Any) -> None:
        conn = self.clients.get(client_id)
        if not conn:
            return
        message = {"id": request_id, "type": "response", "result": result}
        conn.writer.write((json.dumps(message) + "\n").encode("utf-8"))
        await conn.writer.drain()

    async def _send_error(self, client_id: str, request_id: str, error: str) -> None:
        conn = self.clients.get(client_id)
        if not conn:
            return
        message = {"id": request_id, "type": "response", "error": error}
        conn.writer.write((json.dumps(message) + "\n").encode("utf-8"))
        await conn.writer.drain()


def start_server() -> None:
    python = sys.executable
    args = ["-m", "terminalcp", "--server"]
    with open(os.devnull, "wb") as devnull:
        subprocess.Popen(
            [python, *args],
            stdin=devnull,
            stdout=devnull,
            stderr=devnull,
            cwd=os.getcwd(),
            start_new_session=True,
        )


async def start_server_async() -> None:
    start_server()
    await asyncio.sleep(0.1)
