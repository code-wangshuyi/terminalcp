from __future__ import annotations

import itertools
from typing import Any, Dict

_request_counter = itertools.count(1)


def create_request(args: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": f"req-{next(_request_counter)}",
        "type": "request",
        "args": args,
    }
