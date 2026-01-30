from __future__ import annotations

import json
from typing import Any


def parse_json(content: str) -> dict[str, Any]:
    """Parse a JSON string into a dictionary."""
    return json.loads(content)
