"""Shell 类型检测逻辑。"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


_SUPPORTED_SHELLS = {"bash", "zsh", "fish"}


def detect_shell() -> str:
    """检测当前用户的 Shell。

    策略（按可靠性排序）：
    1. ``$SHELL`` 环境变量（用户配置的登录 Shell）
    2. 通过 ``ps`` 获取父进程名称
    3. 默认为 ``bash``

    返回以下之一：``"bash"``、``"zsh"``、``"fish"``
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
    """从类似 ``/bin/zsh`` 的路径中提取已识别的 Shell 名称。"""
    if not shell_path:
        return None
    basename = Path(shell_path).name.lstrip("-")
    if basename in _SUPPORTED_SHELLS:
        return basename
    return None


def _detect_from_parent_process() -> Optional[str]:
    """尝试从父进程检测 Shell 类型（macOS / Linux）。"""
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
