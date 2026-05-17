from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def cache_key(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def raw_cache_path(base: Path, company_id: str, url: str, ext: str = ".html") -> Path:
    return base / company_id / f"{cache_key(url)}{ext}"


def read_cached(path: Path) -> str | None:
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace")
    return None


def write_cached(path: Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return str(path)


def llm_cache_path(base: Path, stage: str, company_id: str, evidence_hash: str) -> Path:
    return base / "llm" / stage / company_id / f"{evidence_hash}.json"


def read_llm_cache(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_llm_cache(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def evidence_bundle_hash(items_count: int, snippet_joined: str) -> str:
    h = hashlib.sha256(f"{items_count}:{snippet_joined[:8000]}".encode()).hexdigest()
    return h[:16]
