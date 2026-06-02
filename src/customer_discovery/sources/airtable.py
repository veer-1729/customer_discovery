from __future__ import annotations

import csv
import logging
import os
import re
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import yaml

from customer_discovery.models.company import CompanyRecord, ExternalLinks, TeamMember
from customer_discovery.sources.base import CompanySource
from customer_discovery.sources.cmu_filters import CMUFilterConfig, FilterCondition
from customer_discovery.sources.registry import register_source

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_cmu_config() -> dict[str, Any]:
    path = _project_root() / "config" / "sources" / "cmu_airtable.yaml"
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _row_value(row: dict[str, str], column: str | None) -> str | None:
    if not column:
        return None
    val = row.get(column, "").strip()
    return val or None


def _split_verticals(raw: str | None) -> list[str]:
    if not raw:
        return []
    parts = re.split(r"[,;\|\n]+", raw)
    return [p.strip() for p in parts if p.strip()]


def _normalize_linkedin(url: str | None) -> str | None:
    if not url:
        return None
    url = url.strip()
    if not url:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if "linkedin.com" in url.lower():
        return f"https://{url.lstrip('/')}"
    return None


def _normalize_employee_bucket(bucket: str | None) -> str | None:
    if not bucket:
        return None
    b = bucket.strip()
    if not b:
        return None
    # CMU cards display "0-10"; config buckets use "1-10".
    if b == "0-10":
        return "1-10"
    return b


def _resolve_view_url(config: dict[str, Any], view: str | None) -> str:
    base = config.get("shared_view_url", "")
    views = config.get("views", {})
    if view:
        key = view.lower().replace(" ", "_").replace(",", "")
        if key in views:
            view_id = views[key]
            # Replace or set jrprS
            if "jrprS=" in base:
                import re

                return re.sub(r"jrprS=[^&]+", f"jrprS={view_id}", base)
            sep = "&" if "?" in base else "?"
            return f"{base}{sep}jrprS={view_id}"
    return base


def _row_to_record(row: dict[str, str], config: dict[str, Any]) -> CompanyRecord | None:
    column_map = config.get("column_map", {})
    program = config.get("program", "CMU")
    name = _row_value(row, column_map.get("name"))
    if not name:
        return None
    website = _row_value(row, column_map.get("website"))
    description = _row_value(row, column_map.get("description"))
    industry_raw = _row_value(row, column_map.get("industry"))
    industries = _split_verticals(industry_raw)
    location = _row_value(row, column_map.get("location"))
    founder = _row_value(row, column_map.get("founder"))
    linkedin = _normalize_linkedin(_row_value(row, column_map.get("linkedin")))
    hiring = _row_value(row, column_map.get("hiring"))
    employees = _normalize_employee_bucket(_row_value(row, column_map.get("employees")))

    team: list[TeamMember] = []
    if founder:
        team.append(TeamMember(name=founder, role="Founder", linkedin_url=linkedin))

    links = ExternalLinks()
    if linkedin:
        links.linkedin = linkedin

    return CompanyRecord(
        id=CompanyRecord.make_id(name, website),
        name=name,
        website=website,
        description=description,
        industry=industries,
        program=program,
        source="cmu",
        source_url=config.get("shared_view_url"),
        team=team,
        links=links,
        raw={
            **row,
            "location": location,
            "founder": founder,
            "linkedin": linkedin,
            "hiring": hiring,
            "employees": employees,
        },
        scraped_at=datetime.now(timezone.utc),
    )


def _csv_has_employee_values(rows: list[dict[str, str]], field: str) -> bool:
    return any((row.get(field) or "").strip() for row in rows)


async def _iter_csv_rows(
    csv_path: Path,
    filter_config: CMUFilterConfig,
    limit: int | None,
) -> AsyncIterator[CompanyRecord]:
    config = load_cmu_config()
    count = 0
    skipped = 0
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)
    effective = filter_config
    if filter_config.employee_size_range and not _csv_has_employee_values(
        all_rows, filter_config.employee_size_field
    ):
        log.warning(
            "CMU CSV has no %r values (gallery export omits this field). "
            "Skipping employee-size filter for this ingest; use a full Airtable CSV export for 1–30 filtering.",
            filter_config.employee_size_field,
        )
        effective = CMUFilterConfig(
            conditions=list(filter_config.conditions),
            conjunction=filter_config.conjunction,
            employee_buckets=list(filter_config.employee_buckets),
            employee_size_field=filter_config.employee_size_field,
        )
    for row in all_rows:
        if not effective.apply_to_row(row):
            skipped += 1
            continue
        record = _row_to_record(row, config)
        if record is None:
            continue
        yield record
        count += 1
        if limit is not None and count >= limit:
            return
    log.info("CMU CSV: kept %s rows (%s filtered out)", count, skipped)


async def _iter_api_rows(
    filter_config: CMUFilterConfig,
    view: str | None,
    limit: int | None,
) -> AsyncIterator[CompanyRecord]:
    api_key = os.environ.get("AIRTABLE_API_KEY")
    if not api_key:
        raise ValueError(
            "AIRTABLE_API_KEY not set. Export CSV from Airtable or set API key in .env"
        )

    config = load_cmu_config()
    base_id = config.get("base_id")
    table_name = config.get("table_name") or config.get("table_id")
    if not base_id or not table_name:
        raise ValueError("config/sources/cmu_airtable.yaml needs base_id and table_name")

    formula = filter_config.build_filter_by_formula()
    params: dict[str, str] = {"pageSize": "100"}
    if formula:
        params["filterByFormula"] = formula

    url = f"https://api.airtable.com/v0/{base_id}/{table_name}"
    headers = {"Authorization": f"Bearer {api_key}"}
    count = 0
    offset: str | None = None

    async with httpx.AsyncClient(headers=headers, timeout=60.0) as client:
        while True:
            req_params = dict(params)
            if offset:
                req_params["offset"] = offset
            resp = await client.get(url, params=req_params)
            resp.raise_for_status()
            data = resp.json()
            for rec in data.get("records", []):
                fields = {k: _stringify(v) for k, v in rec.get("fields", {}).items()}
                if not filter_config.apply_to_row(fields):
                    continue
                record = _row_to_record(fields, config)
                if record is None:
                    continue
                yield record
                count += 1
                if limit is not None and count >= limit:
                    return
            offset = data.get("offset")
            if not offset:
                break


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)


def cmu_dry_run(filter_config: CMUFilterConfig, view: str | None) -> dict[str, Any]:
    config = load_cmu_config()
    base_url = _resolve_view_url(config, view)
    filtered_url = filter_config.append_to_url(base_url)
    formula = filter_config.build_filter_by_formula()
    return {
        "view": view or "default",
        "base_url": base_url,
        "filtered_url": filtered_url,
        "conditions": len(filter_config.conditions),
        "conjunction": filter_config.conjunction,
        "employee_size_range": filter_config.employee_size_range,
        "employee_buckets": filter_config.resolved_employee_buckets(),
        "filter_by_formula": formula,
        "has_api_key": bool(os.environ.get("AIRTABLE_API_KEY")),
    }


@register_source("cmu")
class CMUSource(CompanySource):
    source_id = "cmu"

    async def scrape(
        self,
        *,
        limit: int | None = None,
        **options: Any,
    ) -> AsyncIterator[CompanyRecord]:
        filter_config: CMUFilterConfig = options.get(
            "filter_config", CMUFilterConfig()
        )
        csv_path: Path | None = options.get("csv_path")
        use_api: bool = options.get("use_api", False)
        view: str | None = options.get("view")

        if use_api:
            async for rec in _iter_api_rows(filter_config, view, limit):
                yield rec
            return

        if csv_path is None or not csv_path.exists():
            config = load_cmu_config()
            filtered_url = filter_config.append_to_url(_resolve_view_url(config, view))
            raise ValueError(
                "CMU source needs --csv (Airtable export) or --api with AIRTABLE_API_KEY.\n"
                f"Apply filters in browser: {filtered_url}\n"
                "Then export CSV from that filtered view."
            )

        async for rec in _iter_csv_rows(csv_path, filter_config, limit):
            yield rec
