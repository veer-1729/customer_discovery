from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_ROOT = Path(__file__).resolve().parents[3]


def project_root() -> Path:
    return _ROOT


def load_outreach_config(config_path: Path | str | None = None) -> dict[str, Any]:
    if config_path is None:
        path = _ROOT / "config" / "outreach.yaml"
    else:
        path = Path(config_path)
        if not path.is_absolute():
            path = _ROOT / path
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
