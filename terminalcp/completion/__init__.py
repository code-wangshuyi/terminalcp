"""Shell completion support for terminalcp."""
from __future__ import annotations

from .detect import detect_shell
from .install import install_completion, get_completion_script

__all__ = ["detect_shell", "install_completion", "get_completion_script"]
