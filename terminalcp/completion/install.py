"""Completion installation logic for each supported shell."""
from __future__ import annotations

import importlib.resources
import os
import platform
from pathlib import Path
from typing import Optional

from .detect import detect_shell


# Map shell name -> script filename inside the ``scripts`` package.
_SCRIPT_FILENAMES = {
    "zsh": "_terminalcp.zsh",
    "bash": "terminalcp.bash",
    "fish": "terminalcp.fish",
}


def get_completion_script(shell: str) -> str:
    """Load the completion script for *shell* from package data."""
    filename = _SCRIPT_FILENAMES.get(shell)
    if not filename:
        raise ValueError(f"Unsupported shell: {shell}. Supported: {', '.join(_SCRIPT_FILENAMES)}")

    ref = importlib.resources.files("terminalcp.completion.scripts").joinpath(filename)
    return ref.read_text(encoding="utf-8")


def install_completion(shell: Optional[str] = None) -> None:
    """Detect (or use the given) shell type, then install the matching completion."""
    if shell is None:
        shell = detect_shell()

    print(f"Detected shell: {shell}")

    installers = {
        "zsh": _install_zsh,
        "bash": _install_bash,
        "fish": _install_fish,
    }

    installer = installers.get(shell)
    if installer is None:
        print(f"Shell '{shell}' is not supported for completion installation.")
        print(f"Supported shells: {', '.join(installers)}")
        return

    installer()


# ---------------------------------------------------------------------------
# Per-shell installers
# ---------------------------------------------------------------------------

def _install_zsh() -> None:
    completion_dir = Path.home() / ".zsh" / "completions"
    completion_dir.mkdir(parents=True, exist_ok=True)
    target = completion_dir / "_terminalcp"

    target.write_text(get_completion_script("zsh"))

    _ensure_lines_in_rc(
        Path.home() / ".zshrc",
        [
            (".zsh/completions", "fpath=(~/.zsh/completions $fpath)\n"),
            ("compinit", "autoload -Uz compinit && compinit\n"),
            ("compdef _terminalcp terminalcp", "compdef _terminalcp terminalcp\n"),
        ],
    )

    print("Zsh completion installed to ~/.zsh/completions/_terminalcp")
    print("Restart your shell or run: source ~/.zshrc")


def _install_bash() -> None:
    completion_dir = Path.home() / ".bash_completions.d"
    completion_dir.mkdir(parents=True, exist_ok=True)
    target = completion_dir / "terminalcp.bash"

    target.write_text(get_completion_script("bash"))

    rc_path = _get_bash_rc_path()
    source_line = '[ -f ~/.bash_completions.d/terminalcp.bash ] && source ~/.bash_completions.d/terminalcp.bash\n'
    _ensure_lines_in_rc(
        rc_path,
        [
            ("bash_completions.d/terminalcp", source_line),
        ],
    )

    print(f"Bash completion installed to ~/.bash_completions.d/terminalcp.bash")
    print(f"Restart your shell or run: source {rc_path}")


def _install_fish() -> None:
    config_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    completion_dir = config_dir / "fish" / "completions"
    completion_dir.mkdir(parents=True, exist_ok=True)
    target = completion_dir / "terminalcp.fish"

    target.write_text(get_completion_script("fish"))

    print(f"Fish completion installed to {target}")
    print("Fish will auto-load completions on next shell start.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_bash_rc_path() -> Path:
    """Return the preferred bash rc file path."""
    bashrc = Path.home() / ".bashrc"
    bash_profile = Path.home() / ".bash_profile"

    if bashrc.exists():
        return bashrc
    if platform.system() == "Darwin" and bash_profile.exists():
        return bash_profile
    return bashrc


def _ensure_lines_in_rc(
    rc_path: Path,
    checks_and_lines: list[tuple[str, str]],
) -> None:
    """Append lines to *rc_path* if they are not already present."""
    if rc_path.exists():
        content = rc_path.read_text()
    else:
        content = ""

    updated = False
    for check_string, line_to_add in checks_and_lines:
        if check_string not in content:
            if content and not content.endswith("\n"):
                content += "\n"
            content += line_to_add
            updated = True

    if updated:
        rc_path.write_text(content)
