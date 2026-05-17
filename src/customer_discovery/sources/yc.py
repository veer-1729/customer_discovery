from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx
import yaml
from bs4 import BeautifulSoup

from customer_discovery.models.company import CompanyRecord, ExternalLinks, TeamMember
from customer_discovery.sources.base import CompanySource
from customer_discovery.sources.registry import register_source
from customer_discovery.sources.yc_filters import YCFilterConfig

log = logging.getLogger(__name__)

YC_BASE = "https://www.ycombinator.com"
ALGOLIA_URL = "https://45bwzj1sgc-dsn.algolia.net/1/indexes/*/queries"
INDEX_NAME = "YCCompany_By_Launch_Date_production"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}

_algolia_headers: dict[str, str] | None = None


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_yc_config() -> dict[str, Any]:
    path = _project_root() / "config" / "sources" / "yc.yaml"
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_algolia_headers(client: httpx.Client) -> dict[str, str]:
    global _algolia_headers
    if _algolia_headers is not None:
        return _algolia_headers

    resp = client.get(f"{YC_BASE}/companies", timeout=30.0)
    resp.raise_for_status()
    match = re.search(r"window\.AlgoliaOpts\s*=\s*(\{[^}]+\})", resp.text)
    if not match:
        raise RuntimeError("Could not find AlgoliaOpts on YC companies page")

    opts = json.loads(match.group(1))
    _algolia_headers = {
        "x-algolia-agent": "Algolia for JavaScript (3.35.1); Browser",
        "x-algolia-application-id": opts["app"],
        "x-algolia-api-key": opts["key"],
    }
    log.info("Fetched Algolia credentials (app=%s)", opts["app"])
    return _algolia_headers


def algolia_query(
    client: httpx.Client,
    page: int,
    filter_config: YCFilterConfig,
) -> dict[str, Any]:
    params = filter_config.build_algolia_params()
    params["page"] = str(page)
    body = {"requests": [{"indexName": INDEX_NAME, "params": urlencode(params)}]}
    headers = get_algolia_headers(client)
    resp = client.post(ALGOLIA_URL, params=headers, json=body, timeout=60.0)
    resp.raise_for_status()
    return resp.json()["results"][0]


def algolia_facet_summary(
    client: httpx.Client,
    filter_config: YCFilterConfig,
) -> dict[str, Any]:
    result = algolia_query(client, 0, filter_config)
    return {
        "nbHits": result.get("nbHits", 0),
        "facets": result.get("facets", {}),
        "facetFilters": filter_config.build_algolia_params().get("facetFilters"),
        "numericFilters": filter_config.build_algolia_params().get("numericFilters"),
    }


def hit_to_record(hit: dict[str, Any], program: str = "YC") -> CompanyRecord:
    slug = hit.get("slug", "")
    name = hit.get("name", "")
    website = hit.get("website") or None
    description = hit.get("one_liner") or hit.get("long_description")
    industries = hit.get("industries") or []
    tags = hit.get("tags") or []
    industry = sorted(set(industries) | set(tags))

    record = CompanyRecord(
        id=CompanyRecord.make_id(name, website),
        name=name,
        website=website,
        description=description,
        industry=industry,
        batch=hit.get("batch"),
        program=program,
        source="yc",
        source_url=f"{YC_BASE}/companies/{slug}" if slug else None,
        links=ExternalLinks(),
        raw={
            "slug": slug,
            "status": hit.get("status"),
            "team_size": hit.get("team_size"),
            "regions": hit.get("regions"),
            "all_locations": hit.get("all_locations"),
            "isHiring": hit.get("isHiring"),
            "top_company": hit.get("top_company"),
            "objectID": hit.get("objectID"),
        },
        scraped_at=datetime.now(timezone.utc),
    )
    return record


def _parse_founders_from_next_data(data: dict[str, Any]) -> list[TeamMember]:
    founders: list[TeamMember] = []
    try:
        props = data.get("props", {}).get("pageProps", {})
        company = props.get("company") or props.get("data", {}).get("company") or {}
        for f in company.get("founders", []):
            founders.append(
                TeamMember(
                    name=f.get("full_name", f.get("name", "")),
                    role=f.get("title"),
                    linkedin_url=f.get("linkedin_url") or f.get("linkedin"),
                    github_url=f.get("github_url") or f.get("github"),
                )
            )
    except Exception:
        pass
    return founders


def scrape_founders_for_slug(client: httpx.Client, slug: str) -> list[TeamMember]:
    url = f"{YC_BASE}/companies/{slug}"
    resp = client.get(url, timeout=20.0)
    if not resp.is_success:
        return []
    soup = BeautifulSoup(resp.text, "lxml")
    script = soup.find("script", id="__NEXT_DATA__")
    if script and script.string:
        try:
            data = json.loads(script.string)
            founders = _parse_founders_from_next_data(data)
            if founders:
                return founders
        except json.JSONDecodeError:
            pass
    return []


@register_source("yc")
class YCSource(CompanySource):
    source_id = "yc"

    async def scrape(
        self,
        *,
        limit: int | None = None,
        **options: Any,
    ) -> AsyncIterator[CompanyRecord]:
        filter_config: YCFilterConfig = options["filter_config"]
        fetch_founders: bool = options.get("fetch_founders", False)
        rate_limit_rps: float = options.get("rate_limit_rps", 1.5)
        delay = 1.0 / rate_limit_rps if rate_limit_rps > 0 else 0

        program = options.get("program", "YC")
        count = 0

        with httpx.Client(headers=HEADERS, follow_redirects=True) as client:
            page = 0
            while True:
                result = algolia_query(client, page, filter_config)
                hits = result.get("hits", [])
                if not hits:
                    break

                for hit in hits:
                    record = hit_to_record(hit, program=program)
                    if fetch_founders and hit.get("slug"):
                        time.sleep(delay)
                        record.team = scrape_founders_for_slug(client, hit["slug"])
                    yield record
                    count += 1
                    if limit is not None and count >= limit:
                        return

                nb_pages = result.get("nbPages", 1)
                page += 1
                if page >= nb_pages:
                    break
                time.sleep(delay)
