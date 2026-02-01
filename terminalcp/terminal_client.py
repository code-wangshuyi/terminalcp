from __future__ import annotations

import asyncio
import json
import os
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Callable, Dict, Optional

from .messages import create_request
from .terminal_server import start_server_async


def get_client_version() -> str:
    try:
        return version("terminalcp")
    except PackageNotFoundError:
        return "0.0.0"


class TerminalClient:
    def __init__(self) -> None:
        self.socket_path = os.path.join(os.path.expanduser("~"), ".terminalcp", "server.sock")
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.pending_requests: Dict[str, asyncio.Future[Any]] = {}
        self.event_handlers: Dict[str, Callable[[Dict[str, Any]], None]] = {}
        self.connected = False
        self._connect_lock = asyncio.Lock()
        self._reader_task: Optional[asyncio.Task[None]] = None

    async def connect(self, skip_version_check: bool = False, auto_start: bool = True) -> None:
        async with self._connect_lock:
            if self.connected:
                return

            if await self._is_server_running():
                await self._connect_to_server()
                if not skip_version_check:
                    await self._check_server_version()
            else:
                if not auto_start:
                    raise RuntimeError("No server running")
                await start_server_async()

                retries = 10
                while retries > 0:
                    await asyncio.sleep(0.1)
                    if await self._is_server_running():
                        break
                    retries -= 1

                if retries == 0:
                    raise RuntimeError("Failed to start server")

                await self._connect_to_server()

    async def request(self, args: Dict[str, Any]) -> Any:
        action = args.get("action")
        if not self.connected:
            skip_version_check = action in {"kill-server", "version"}
            auto_start = action == "start"
            await self.connect(skip_version_check=skip_version_check, auto_start=auto_start)
        return await self._send_request(args)

    def register_event_handler(self, event: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        self.event_handlers[event] = handler

    def close(self) -> None:
        if self.writer:
            self.writer.close()
        self.connected = False
        self.reader = None
        self.writer = None
        if self._reader_task:
            self._reader_task.cancel()
            self._reader_task = None

    async def _check_server_version(self) -> None:
        client_version = get_client_version()
        try:
            server_version = await self._send_request({"action": "version"})
        except Exception as exc:
            raise RuntimeError(
                "Server version mismatch: server does not support version checks, "
                f"client is v{client_version}. Please run 'terminalcp kill-server' "
                "to stop the old server (this will terminate all managed processes)."
            ) from exc

        if server_version != client_version:
            raise RuntimeError(
                f"Server version mismatch: server is v{server_version}, client is v{client_version}. "
                "Please run 'terminalcp kill-server' to stop the old server (this will terminate all managed processes)."
            )

    async def _is_server_running(self) -> bool:
        if not os.path.exists(self.socket_path):
            return False
        try:
            reader, writer = await asyncio.wait_for(asyncio.open_unix_connection(self.socket_path), timeout=0.1)
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False

    async def _connect_to_server(self) -> None:
        self.reader, self.writer = await asyncio.open_unix_connection(self.socket_path)
        self.connected = True
        self._reader_task = asyncio.create_task(self._reader_loop())

    async def _reader_loop(self) -> None:
        assert self.reader is not None
        try:
            while not self.reader.at_eof():
                line = await self.reader.readline()
                if not line:
                    break
                line_str = line.decode("utf-8", errors="replace").strip()
                if not line_str:
                    continue
                try:
                    message = json.loads(line_str)
                except json.JSONDecodeError:
                    continue
                await self._handle_message(message)
        except asyncio.CancelledError:
            return

        self.connected = False
        for future in self.pending_requests.values():
            if not future.done():
                future.set_exception(RuntimeError("Server connection closed"))
        self.pending_requests.clear()

    async def _handle_message(self, message: Dict[str, Any]) -> None:
        msg_type = message.get("type")
        if msg_type == "response":
            request_id = message.get("id")
            future = self.pending_requests.pop(request_id, None)
            if future is None:
                return
            if message.get("error"):
                future.set_exception(RuntimeError(message.get("error")))
            else:
                future.set_result(message.get("result"))
        elif msg_type == "event":
            event = message.get("event")
            handler = self.event_handlers.get(event)
            if handler:
                handler(message)

    async def _send_request(self, args: Dict[str, Any]) -> Any:
        if not self.writer:
            raise RuntimeError("Not connected to server")
        message = create_request(args)
        request_id = message["id"]
        loop = asyncio.get_running_loop()
        future: asyncio.Future[Any] = loop.create_future()
        self.pending_requests[request_id] = future

        self.writer.write((json.dumps(message) + "\n").encode("utf-8"))
        await self.writer.drain()

        try:
            return await asyncio.wait_for(future, timeout=5)
        except asyncio.TimeoutError as exc:
            self.pending_requests.pop(request_id, None)
            raise RuntimeError("Request timeout") from exc
