from __future__ import annotations

from typing import Iterable, List

SPECIAL_KEYS = {
    # Navigation keys
    "Up": "\x1b[A",
    "Down": "\x1b[B",
    "Left": "\x1b[D",
    "Right": "\x1b[C",
    "Home": "\x1b[H",
    "End": "\x1b[F",

    # Page navigation
    "PageUp": "\x1b[5~",
    "PageDown": "\x1b[6~",
    "PgUp": "\x1b[5~",
    "PgDn": "\x1b[6~",
    "PPage": "\x1b[5~",
    "NPage": "\x1b[6~",

    # Editing keys
    "Insert": "\x1b[2~",
    "Delete": "\x1b[3~",
    "IC": "\x1b[2~",
    "DC": "\x1b[3~",

    # Special characters
    "Enter": "\r",
    "Tab": "\t",
    "BTab": "\x1b[Z",
    "Space": " ",
    "Escape": "\x1b",
    "Esc": "\x1b",
    "BSpace": "\x7f",
    "Backspace": "\x7f",

    # Function keys
    "F1": "\x1bOP",
    "F2": "\x1bOQ",
    "F3": "\x1bOR",
    "F4": "\x1bOS",
    "F5": "\x1b[15~",
    "F6": "\x1b[17~",
    "F7": "\x1b[18~",
    "F8": "\x1b[19~",
    "F9": "\x1b[20~",
    "F10": "\x1b[21~",
    "F11": "\x1b[23~",
    "F12": "\x1b[24~",

    # Keypad keys
    "KP0": "\x1bOp",
    "KP1": "\x1bOq",
    "KP2": "\x1bOr",
    "KP3": "\x1bOs",
    "KP4": "\x1bOt",
    "KP5": "\x1bOu",
    "KP6": "\x1bOv",
    "KP7": "\x1bOw",
    "KP8": "\x1bOx",
    "KP9": "\x1bOy",
    "KP/": "\x1bOo",
    "KP*": "\x1bOj",
    "KP-": "\x1bOm",
    "KP+": "\x1bOk",
    "KP.": "\x1bOn",
    "KPEnter": "\x1bOM",
}

CONTROL_CHARS = {
    "@": "\x00",
    "a": "\x01",
    "b": "\x02",
    "c": "\x03",
    "d": "\x04",
    "e": "\x05",
    "f": "\x06",
    "g": "\x07",
    "h": "\x08",
    "i": "\x09",
    "j": "\x0a",
    "k": "\x0b",
    "l": "\x0c",
    "m": "\x0d",
    "n": "\x0e",
    "o": "\x0f",
    "p": "\x10",
    "q": "\x11",
    "r": "\x12",
    "s": "\x13",
    "t": "\x14",
    "u": "\x15",
    "v": "\x16",
    "w": "\x17",
    "x": "\x18",
    "y": "\x19",
    "z": "\x1a",
    "[": "\x1b",
    "\\": "\x1c",
    "]": "\x1d",
    "^": "\x1e",
    "_": "\x1f",
    "?": "\x7f",
}


def parse_key_sequence(key: str) -> str:
    if not key:
        return ""

    if key.startswith("0x"):
        try:
            code_point = int(key, 16)
        except ValueError:
            return key
        return chr(code_point)

    if len(key) == 2 and key[0] == "^":
        char = key[1].lower()
        if char in CONTROL_CHARS:
            return CONTROL_CHARS[char]
        return key

    modifiers: List[str] = []
    remaining = key

    while True:
        if len(remaining) < 3:
            break
        if remaining[1] != "-":
            break
        modifier = remaining[0].upper()
        if modifier not in ("C", "M", "S"):
            break
        remainder = remaining[2:]
        if not remainder:
            break
        if modifier not in modifiers:
            modifiers.append(modifier)
        remaining = remainder

    base_sequence = SPECIAL_KEYS.get(remaining)

    if base_sequence is None:
        if "S" in modifiers and len(remaining) == 1:
            base_sequence = remaining.upper()
            modifiers = [m for m in modifiers if m != "S"]
        else:
            base_sequence = remaining
    else:
        if "S" in modifiers and remaining == "Tab":
            base_sequence = SPECIAL_KEYS["BTab"]
            modifiers = [m for m in modifiers if m != "S"]

    if "C" in modifiers and len(base_sequence) == 1:
        char = base_sequence.lower()
        if char in CONTROL_CHARS:
            base_sequence = CONTROL_CHARS[char]

    if "M" in modifiers:
        base_sequence = "\x1b" + base_sequence

    return base_sequence


def parse_key_input(input_value: str | Iterable[str]) -> str:
    if isinstance(input_value, str):
        if input_value.startswith("::"):
            return parse_key_sequence(input_value[2:])
        return input_value

    if isinstance(input_value, Iterable):
        parts: List[str] = []
        for item in input_value:
            if item.startswith("::"):
                parts.append(parse_key_sequence(item[2:]))
            else:
                parts.append(item)
        return "".join(parts)

    return ""


def build_input(*parts: str) -> str:
    return "".join(parse_key_sequence(part) for part in parts)
