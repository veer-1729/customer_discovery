from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_ROOT = Path(__file__).resolve().parents[3]


def project_root() -> Path:
    return _ROOT


def load_yaml(name: str) -> dict[str, Any]:
    path = _ROOT / "config" / name
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_research_config() -> dict[str, Any]:
    return load_yaml("research.yaml")


def load_product_config() -> dict[str, Any]:
    return load_yaml("product.yaml")


def load_icp_config() -> dict[str, Any]:
    return load_yaml("icp.yaml")
