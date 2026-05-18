from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def read_staged(path: Path, model: type[T]) -> list[T]:
    if not path.exists():
        return []
    out: list[T] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(model.model_validate_json(line))
    return out


def load_ids_staged(path: Path, model: type[T], id_field: str = "company_id") -> set[str]:
    return {getattr(r, id_field) for r in read_staged(path, model)}


def append_staged(path: Path, record: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(record.model_dump_json() + "\n")


def write_staged(path: Path, records: list[BaseModel]) -> None:
    """Replace staged JSONL with records (one JSON object per line)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(record.model_dump_json() + "\n")


def index_by_company(path: Path, model: type[T]) -> dict[str, T]:
    return {getattr(r, "company_id"): r for r in read_staged(path, model)}


def write_json_line(path: Path, record: BaseModel) -> None:
    append_staged(path, record)


def dump_json(obj: BaseModel) -> str:
    return obj.model_dump_json()


def parse_json_line(line: str, model: type[T]) -> T:
    return model.model_validate(json.loads(line))
