from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from .key_parser import build_input, parse_key_input, parse_key_sequence
from .terminal_manager import TerminalManager

try:
    __version__ = version("terminalcp")
except PackageNotFoundError:  # pragma: no cover - fallback for editable usage
    __version__ = "0.0.0"

__all__ = [
    "TerminalManager",
    "build_input",
    "parse_key_input",
    "parse_key_sequence",
]
