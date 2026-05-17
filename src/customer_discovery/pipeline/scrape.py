from __future__ import annotations

import logging
from pathlib import Path

from customer_discovery.models.company import CompanyRecord
from customer_discovery.pipeline.dedup import DedupIndex
from customer_discovery.pipeline.normalize import normalize_record
from customer_discovery.sources.base import CompanySource
from customer_discovery.storage.jsonl import read_jsonl, write_jsonl

log = logging.getLogger(__name__)


def default_output_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "companies.jsonl"


async def run_scrape(
    source: CompanySource,
    *,
    output: Path,
    limit: int | None = None,
    resume: bool = False,
    source_options: dict | None = None,
) -> dict[str, int]:
    source_options = source_options or {}
    existing = read_jsonl(output) if resume and output.exists() else []
    index = DedupIndex(existing)
    existing_ids = {r.id for r in existing} if resume else set()

    added = 0
    skipped = 0

    async for record in source.scrape(limit=limit, **source_options):
        normalized = normalize_record(record)
        if resume and normalized.id in existing_ids:
            skipped += 1
            continue
        index.add(normalized)
        existing_ids.add(normalized.id)
        added += 1
        log.debug("Added %s (%s)", normalized.name, normalized.id)

    write_jsonl(output, index.values())
    return {
        "total": len(index),
        "added_this_run": added,
        "skipped_resume": skipped,
    }
