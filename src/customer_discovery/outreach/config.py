from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_ROOT = Path(__file__).resolve().parents[3]


def project_root() -> Path:
    return _ROOT


def load_outreach_config() -> dict[str, Any]:
    path = _ROOT / "config" / "outreach.yaml"
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
