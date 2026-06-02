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


def load_yaml_path(path: Path | str) -> dict[str, Any]:
    p = Path(path)
    if not p.is_absolute():
        p = _ROOT / p
    if not p.exists():
        raise FileNotFoundError(f"Config not found: {p}")
    with p.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_research_config(config_path: Path | str | None = None) -> dict[str, Any]:
    if config_path is None:
        return load_yaml("research.yaml")
    return load_yaml_path(config_path)


def load_product_config() -> dict[str, Any]:
    return load_yaml("product.yaml")


def load_icp_config() -> dict[str, Any]:
    return load_yaml("icp.yaml")
