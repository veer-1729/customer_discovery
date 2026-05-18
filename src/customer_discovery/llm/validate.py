from __future__ import annotations

from typing import Any


def clamp_score(value: Any, *, default: int = 50) -> int:
    """Coerce LLM numeric scores to 0–100 (models sometimes return 150, etc.)."""
    if value is None:
        return default
    try:
        n = int(float(value))
    except (TypeError, ValueError):
        return default
    return max(0, min(100, n))
