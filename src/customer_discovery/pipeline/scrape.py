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


def has_team_seed(record: CompanyRecord) -> bool:
    """True when scrape already stored at least one named team member."""
    return any(m.name and m.name.strip() for m in record.team)


def founder_fetch_complete(record: CompanyRecord) -> bool:
    """True when founder page was fetched and stored (team and/or flag)."""
    if has_team_seed(record):
        return True
    return bool((record.raw or {}).get("founders_page_fetched"))


def slugs_with_team_seed(existing: list[CompanyRecord]) -> set[str]:
    """YC slugs that should not trigger another /companies/{slug} HTTP request."""
    slugs: set[str] = set()
    for rec in existing:
        slug = (rec.raw or {}).get("slug")
        if slug and founder_fetch_complete(rec):
            slugs.add(str(slug))
    return slugs


def prepare_source_options(
    source_options: dict | None,
    existing: list[CompanyRecord],
) -> dict:
    """Inject skip_founder_slugs for YC when --founders and we already have team data."""
    opts = dict(source_options or {})
    if opts.get("fetch_founders"):
        opts["skip_founder_slugs"] = slugs_with_team_seed(existing)
    return opts


async def run_scrape(
    source: CompanySource,
    *,
    output: Path,
    limit: int | None = None,
    resume: bool = False,
    source_options: dict | None = None,
) -> dict[str, int]:
    existing = read_jsonl(output) if output.exists() else []
    source_options = prepare_source_options(source_options, existing)

    index = DedupIndex(existing)
    existing_by_id = {r.id: r for r in existing}
    existing_ids = set(existing_by_id) if resume else set()
    fetch_founders = bool(source_options.get("fetch_founders"))

    added = 0
    updated_team = 0
    skipped = 0
    skipped_founder_fetch = len(source_options.get("skip_founder_slugs") or [])

    async for record in source.scrape(limit=limit, **source_options):
        normalized = normalize_record(record)
        if resume and normalized.id in existing_ids:
            prior = existing_by_id.get(normalized.id)
            if prior and fetch_founders and not founder_fetch_complete(prior):
                merged = index.add(normalized)
                existing_by_id[normalized.id] = merged
                if has_team_seed(merged) or (normalized.raw or {}).get("founders_page_fetched"):
                    updated_team += 1
                    log.debug("Backfilled founders for %s", normalized.id)
                continue
            skipped += 1
            continue
        merged = index.add(normalized)
        existing_ids.add(normalized.id)
        existing_by_id[normalized.id] = merged
        added += 1
        log.debug("Added %s (%s)", normalized.name, normalized.id)

    write_jsonl(output, index.values())
    return {
        "total": len(index),
        "added_this_run": added,
        "updated_team_this_run": updated_team,
        "skipped_resume": skipped,
        "skipped_founder_fetch": skipped_founder_fetch,
    }
