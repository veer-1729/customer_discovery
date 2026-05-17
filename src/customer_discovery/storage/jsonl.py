from __future__ import annotations

import json
from pathlib import Path

from customer_discovery.models.company import CompanyRecord


def read_jsonl(path: Path) -> list[CompanyRecord]:
    if not path.exists():
        return []
    records: list[CompanyRecord] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(CompanyRecord.model_validate_json(line))
    return records


def write_jsonl(path: Path, records: list[CompanyRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(rec.model_dump_json() + "\n")
    tmp.replace(path)


def load_ids(path: Path) -> set[str]:
    return {r.id for r in read_jsonl(path)}
