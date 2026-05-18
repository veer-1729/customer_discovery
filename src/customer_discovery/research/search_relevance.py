from __future__ import annotations

from urllib.parse import urlparse

from customer_discovery.pipeline.normalize import normalize_domain
from customer_discovery.research.search.base import SearchResult

# Third-party ATS / job boards we accept when the company posts there.
ATS_HOST_SUFFIXES: tuple[str, ...] = (
    "ashbyhq.com",
    "lever.co",
    "greenhouse.io",
    "workable.com",
    "breezy.hr",
    "rippling.com",
    "gem.com",
)

# Aggregators and common homonym traps — never fetch for evidence.
BLOCKED_HOST_SUFFIXES: tuple[str, ...] = (
    "indeed.com",
    "linkedin.com",
    "glassdoor.com",
    "internshala.com",
    "ziprecruiter.com",
    "monster.com",
    "simplyhired.com",
    "dice.com",
    "wellfound.com",
    "angel.co",
    "crunchbase.com",
)


def company_domain_from_website(website: str | None) -> str | None:
    return normalize_domain(website) if website else None


def host_matches_company_domain(host: str, company_domain: str) -> bool:
    host = host.lower().removeprefix("www.")
    company_domain = company_domain.lower().removeprefix("www.")
    return host == company_domain or host.endswith("." + company_domain)


def is_allowed_ats_host(host: str) -> bool:
    host = host.lower().removeprefix("www.")
    return any(host == s or host.endswith("." + s) for s in ATS_HOST_SUFFIXES)


def is_blocked_search_host(host: str) -> bool:
    host = host.lower().removeprefix("www.")
    return any(host == s or host.endswith("." + s) for s in BLOCKED_HOST_SUFFIXES)


def is_yc_company_page(url: str, *, source_url: str | None, yc_slug: str | None) -> bool:
    if not yc_slug or not source_url or "ycombinator.com" not in source_url:
        return False
    host = normalize_domain(url)
    if host != "ycombinator.com":
        return False
    path = urlparse(url).path.lower()
    return f"/companies/{yc_slug.lower()}" in path


def is_relevant_search_url(
    url: str,
    *,
    company_domain: str | None,
    source_url: str | None = None,
    yc_slug: str | None = None,
) -> bool:
    """True when a search result URL plausibly belongs to this company."""
    host = normalize_domain(url)
    if not host:
        return False
    if is_blocked_search_host(host):
        return False
    if company_domain and host_matches_company_domain(host, company_domain):
        return True
    if is_allowed_ats_host(host):
        return True
    if is_yc_company_page(url, source_url=source_url, yc_slug=yc_slug):
        return True
    return False


def filter_search_results(
    results: list[SearchResult],
    *,
    company_domain: str | None,
    source_url: str | None = None,
    yc_slug: str | None = None,
) -> list[SearchResult]:
    return [
        r
        for r in results
        if is_relevant_search_url(
            r.url,
            company_domain=company_domain,
            source_url=source_url,
            yc_slug=yc_slug,
        )
    ]


def format_search_query(template: str, *, company_name: str, website: str | None, raw: dict | None) -> str | None:
    """Format a search template; return None if required fields (e.g. domain) are missing."""
    domain = company_domain_from_website(website) or ""
    slug = str((raw or {}).get("slug") or "")
    if "{company_domain}" in template and not domain:
        return None
    return template.format(
        company_name=company_name,
        company_domain=domain,
        company_website=website or "",
        yc_slug=slug,
    )


def search_context_from_company(company) -> dict[str, str | None]:
    """Build relevance kwargs from a CompanyRecord."""
    return {
        "company_domain": company_domain_from_website(
            str(company.website) if company.website else None
        ),
        "source_url": str(company.source_url) if company.source_url else None,
        "yc_slug": str((company.raw or {}).get("slug") or "") or None,
    }
