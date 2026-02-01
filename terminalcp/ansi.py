from __future__ import annotations

import re

_ANSI_ESCAPE_RE = re.compile(
    r"""
    \x1B
    (?:
        [@-Z\\-_]
      | \[[0-?]*[ -/]*[@-~]
      | \].*?(?:\x07|\x1b\\)
    )
    """,
    re.VERBOSE | re.DOTALL,
)


def strip_ansi(text: str) -> str:
    if not text:
        return text
    return _ANSI_ESCAPE_RE.sub("", text)
