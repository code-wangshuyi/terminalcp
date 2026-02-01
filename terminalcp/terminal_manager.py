from __future__ import annotations

import asyncio
import os
import pty
import secrets
import struct
import subprocess
import termios
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

import pyte

from .ansi import strip_ansi


@dataclass
class ManagedTerminal:
    id: str
    command: str
    cwd: str
    process: subprocess.Popen[str]
    master_fd: int
    screen: pyte.Screen
    stream: pyte.Stream
    started_at: float
    raw_output: str = ""
    last_stream_read_position: int = 0
    running: bool = True
    exit_code: Optional[int] = None
    input_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    output_lock: threading.Lock = field(default_factory=threading.Lock)
    cols: int = 80
    rows: int = 24
    use_byte_stream: bool = False


class TerminalManager:
    def __init__(self) -> None:
        self._processes: Dict[str, ManagedTerminal] = {}
        self._output_handlers: Dict[str, Callable[[str, str], None]] = {}

    async def start(self, command: str, options: Optional[Dict[str, str]] = None) -> str:
        options = options or {}
        session_id = options.get("name") or f"proc-{secrets.token_hex(6)}"
        if session_id in self._processes:
            raise RuntimeError(f"Session '{session_id}' already exists")

        cols = 80
        rows = 24

        try:
            screen: pyte.Screen = pyte.HistoryScreen(cols, rows, history=10000)
        except TypeError:
            screen = pyte.HistoryScreen(cols, rows)
            if hasattr(screen, "history"):
                try:
                    screen.history.maxlen = 10000
                except Exception:
                    pass

        stream: pyte.Stream
        use_byte_stream = hasattr(pyte, "ByteStream")
        if use_byte_stream:
            stream = pyte.ByteStream(screen)
        else:
            stream = pyte.Stream(screen)

        master_fd, slave_fd = pty.openpty()
        try:
            os.set_blocking(master_fd, False)
        except AttributeError:
            pass

        env = os.environ.copy()
        env.update(
            {
                "TERM": "xterm-256color",
                "COLORTERM": "truecolor",
                "FORCE_COLOR": "1",
            }
        )

        shell = env.get("SHELL", "/bin/bash")
        proc = subprocess.Popen(
            [shell, "-c", command],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            cwd=options.get("cwd") or os.getcwd(),
            env=env,
            start_new_session=True,
        )
        os.close(slave_fd)

        managed = ManagedTerminal(
            id=session_id,
            command=command,
            cwd=options.get("cwd") or os.getcwd(),
            process=proc,
            master_fd=master_fd,
            screen=screen,
            stream=stream,
            started_at=time.time(),
            cols=cols,
            rows=rows,
            use_byte_stream=use_byte_stream,
        )
        self._processes[session_id] = managed

        loop = asyncio.get_running_loop()
        loop.add_reader(master_fd, self._on_pty_data, session_id)
        loop.create_task(self._wait_for_exit(session_id))

        return session_id

    async def stop(self, session_id: str) -> None:
        proc = self._processes.get(session_id)
        if not proc:
            raise RuntimeError(f"Process not found: {session_id}")

        self._output_handlers.pop(session_id, None)
        await self._terminate_process(proc)
        self._cleanup_process(proc)
        self._processes.pop(session_id, None)

    async def stop_all(self) -> None:
        for session_id in list(self._processes.keys()):
            await self.stop(session_id)

    async def send_input(self, session_id: str, data: str) -> None:
        proc = self._processes.get(session_id)
        if not proc:
            raise RuntimeError(f"Session not found: {session_id}")

        if not proc.running:
            raise RuntimeError(
                f"Session {session_id} is not running (pid: {proc.process.pid}, "
                f"exit code: {proc.exit_code if proc.exit_code is not None else 'unknown'}). "
                "Check stdout or stream."
            )

        async with proc.input_lock:
            buffer = ""
            i = 0
            while i < len(data):
                char = data[i]
                if char == "\r":
                    if i + 1 < len(data) and data[i + 1] == "\n":
                        buffer += "\r\n"
                        i += 1
                    else:
                        if buffer:
                            self._write_to_pty(proc, buffer)
                            buffer = ""
                        await asyncio.sleep(0.2)
                        self._write_to_pty(proc, "\r")
                else:
                    buffer += char
                i += 1

            if buffer:
                self._write_to_pty(proc, buffer)

    async def get_output(self, session_id: str, lines: Optional[int] = None) -> str:
        proc = self._processes.get(session_id)
        if not proc:
            raise RuntimeError(f"Process not found: {session_id}")

        with proc.output_lock:
            all_lines = self._screen_lines(proc)

        while all_lines and not all_lines[-1].strip():
            all_lines.pop()

        if lines is not None and len(all_lines) > lines:
            all_lines = all_lines[-lines:]

        return "\n".join(all_lines)

    async def get_stream(
        self, session_id: str, since_last: bool = False, strip_ansi_codes: Optional[bool] = True
    ) -> str:
        proc = self._processes.get(session_id)
        if not proc:
            raise RuntimeError(f"Process not found: {session_id}")

        with proc.output_lock:
            if since_last:
                output = proc.raw_output[proc.last_stream_read_position :]
                proc.last_stream_read_position = len(proc.raw_output)
            else:
                output = proc.raw_output

        if strip_ansi_codes is not False and output:
            output = strip_ansi(output)

        return output

    def get_terminal_size(self, session_id: str) -> Dict[str, int]:
        proc = self._processes.get(session_id)
        if not proc:
            raise RuntimeError(f"Process not found: {session_id}")

        history_lines = 0
        if hasattr(proc.screen, "history"):
            history = proc.screen.history
            top = getattr(history, "top", [])
            bottom = getattr(history, "bottom", [])
            history_lines = len(top) + len(bottom)

        return {
            "rows": proc.rows,
            "cols": proc.cols,
            "scrollback_lines": history_lines + proc.screen.lines,
        }

    def resize_terminal(self, session_id: str, cols: int, rows: int) -> None:
        proc = self._processes.get(session_id)
        if not proc:
            raise RuntimeError(f"Process not found: {session_id}")

        proc.cols = cols
        proc.rows = rows

        try:
            proc.screen.resize(rows, cols)
        except Exception:
            pass

        try:
            self._set_pty_size(proc.master_fd, rows, cols)
        except Exception:
            pass

    def list_processes(self) -> list[Dict[str, object]]:
        return [
            {
                "id": proc.id,
                "command": proc.command,
                "cwd": proc.cwd,
                "started_at": proc.started_at,
                "running": proc.running,
                "pid": proc.process.pid,
            }
            for proc in self._processes.values()
        ]

    def get_process(self, session_id: str) -> Optional[ManagedTerminal]:
        return self._processes.get(session_id)

    def on_output(self, session_id: str, handler: Callable[[str, str], None]) -> None:
        self._output_handlers[session_id] = handler

    def off_output(self, session_id: str) -> None:
        self._output_handlers.pop(session_id, None)

    def _write_to_pty(self, proc: ManagedTerminal, data: str) -> None:
        try:
            os.write(proc.master_fd, data.encode("utf-8", errors="replace"))
        except BrokenPipeError as exc:
            raise RuntimeError("Process is not accepting input") from exc

    def _on_pty_data(self, session_id: str) -> None:
        proc = self._processes.get(session_id)
        if not proc:
            return

        try:
            data = os.read(proc.master_fd, 65536)
        except BlockingIOError:
            return
        except OSError:
            return

        if not data:
            return

        text = data.decode("utf-8", errors="replace")
        with proc.output_lock:
            proc.raw_output += text
            if proc.use_byte_stream:
                proc.stream.feed(data)
            else:
                proc.stream.feed(text)

        handler = self._output_handlers.get(session_id)
        if handler:
            handler(session_id, text)

    async def _wait_for_exit(self, session_id: str) -> None:
        proc = self._processes.get(session_id)
        if not proc:
            return

        exit_code = await asyncio.to_thread(proc.process.wait)
        proc.running = False
        proc.exit_code = exit_code

        try:
            asyncio.get_running_loop().remove_reader(proc.master_fd)
        except Exception:
            pass
        try:
            os.close(proc.master_fd)
        except Exception:
            pass

        signal_num = -exit_code if exit_code < 0 else None
        code_display = abs(exit_code) if exit_code < 0 else exit_code
        if signal_num is not None:
            exit_msg = f"\n[Process exited with code {code_display} (signal: {signal_num})]\n"
        else:
            exit_msg = f"\n[Process exited with code {exit_code}]\n"
        with proc.output_lock:
            proc.raw_output += exit_msg
            if proc.use_byte_stream:
                proc.stream.feed(exit_msg.encode("utf-8", errors="replace"))
            else:
                proc.stream.feed(exit_msg)

    async def _terminate_process(self, proc: ManagedTerminal) -> None:
        if proc.process.poll() is None:
            try:
                proc.process.terminate()
            except Exception:
                pass
        try:
            await asyncio.to_thread(proc.process.wait, timeout=1)
        except Exception:
            try:
                proc.process.kill()
            except Exception:
                pass
            try:
                await asyncio.to_thread(proc.process.wait, timeout=1)
            except Exception:
                pass

    def _cleanup_process(self, proc: ManagedTerminal) -> None:
        try:
            asyncio.get_running_loop().remove_reader(proc.master_fd)
        except Exception:
            pass
        try:
            os.close(proc.master_fd)
        except Exception:
            pass

    def _set_pty_size(self, fd: int, rows: int, cols: int) -> None:
        size = struct.pack("HHHH", rows, cols, 0, 0)
        import fcntl

        fcntl.ioctl(fd, termios.TIOCSWINSZ, size)

    def _screen_lines(self, proc: ManagedTerminal) -> list[str]:
        lines: list[str] = []
        if hasattr(proc.screen, "history"):
            history = proc.screen.history
            top = getattr(history, "top", [])
            for line in top:
                lines.append(self._line_to_str(line))

        for line in proc.screen.display:
            lines.append(line.rstrip())
        return lines

    def _line_to_str(self, line: object) -> str:
        if isinstance(line, str):
            return line.rstrip()
        try:
            return "".join(ch.data for ch in line).rstrip()
        except Exception:
            return str(line).rstrip()
