"""Shell type detection logic."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


_SUPPORTED_SHELLS = {"bash", "zsh", "fish"}


def detect_shell() -> str:
    """Detect the current user's shell.

    Strategy (ordered by reliability):
    1. ``$SHELL`` environment variable (user's configured login shell)
    2. Parent process name via ``ps``
    3. Default to ``bash``

    Returns one of: ``"bash"``, ``"zsh"``, ``"fish"``
    """
    shell_env = os.environ.get("SHELL", "")
    name = _extract_shell_name(shell_env)
    if name:
        return name

    parent = _detect_from_parent_process()
    if parent:
        return parent

    return "bash"


def _extract_shell_name(shell_path: str) -> Optional[str]:
    """Extract a recognised shell name from a path like ``/bin/zsh``."""
    if not shell_path:
        return None
    basename = Path(shell_path).name.lstrip("-")
    if basename in _SUPPORTED_SHELLS:
        return basename
    return None


def _detect_from_parent_process() -> Optional[str]:
    """Try to detect the shell from the parent process (macOS / Linux)."""
    try:
        import subprocess

        ppid = os.getppid()
        result = subprocess.run(
            ["ps", "-p", str(ppid), "-o", "comm="],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            return _extract_shell_name(result.stdout.strip())
    except Exception:
        pass
    return None
