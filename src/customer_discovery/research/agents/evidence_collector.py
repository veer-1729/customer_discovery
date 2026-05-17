from __future__ import annotations

from pathlib import Path
from typing import Any

from customer_discovery.models.company import CompanyRecord
from customer_discovery.models.evidence import EvidenceBundle, ResearchTrace, compute_coverage
from customer_discovery.research.fetch import PageFetcher
from customer_discovery.research.tools import (
    blog_changelog,
    careers,
    docs,
    general_search,
    github,
    homepage,
    known_links,
    seed_metadata,
    status_page,
)
from customer_discovery.research.tools.base import ToolContext
from customer_discovery.research.tools.search_fallback import SearchFallbackTool


def collect_evidence(
    company: CompanyRecord,
    cfg: dict[str, Any],
    *,
    raw_cache_dir: Path,
    search_enabled: bool = True,
    force_refetch: bool = False,
) -> EvidenceBundle:
    SearchFallbackTool.configure(cfg, enabled=search_enabled)
    ac = cfg.get("agentic_collection", {})
    fetcher = PageFetcher(
        timeout=float(ac.get("request_timeout_seconds", 15)),
        user_agent=ac.get("user_agent", "CustomerDiscoveryBot/0.1"),
    )
    ctx = ToolContext(
        company=company,
        cfg=cfg,
        raw_cache_dir=raw_cache_dir,
        fetcher=fetcher,
        search_enabled=search_enabled,
        force_refetch=force_refetch,
    )
    trace = ResearchTrace()
    max_calls = int(ac.get("max_tool_calls_per_company", 20))

    def run_step(name: str, fn) -> None:
        nonlocal max_calls
        if ctx.tool_calls >= max_calls:
            trace.failures.append(f"max_tool_calls exceeded before {name}")
            return
        trace.probes_attempted.append(name)
        fn(ctx)

    run_step("seed_metadata", seed_metadata.run_seed_metadata)
    run_step("homepage", homepage.run_homepage)
    run_step("known_links", known_links.run_known_links_extract)
    run_step("careers", careers.run_careers)
    run_step("docs", docs.run_docs)
    run_step("status", status_page.run_status_page)
    run_step("blog_changelog", blog_changelog.run_blog_changelog)
    run_step("github", github.run_github)

    coverage = compute_coverage(ctx.items)
    if search_enabled:
        run_step(
            "agent_search_fallback",
            lambda c: general_search.run_agent_search_fallback(
                c, coverage.total_successful_sources
            ),
        )
        coverage = compute_coverage(ctx.items)

    trace.tool_calls = ctx.tool_calls
    for item in ctx.items:
        if item.url:
            trace.urls_attempted.append(item.url)
        if item.error:
            trace.failures.append(f"{item.source_type}: {item.error}")

    return EvidenceBundle(
        company_id=company.id,
        company_name=company.name,
        website=str(company.website) if company.website else None,
        source=company.source,
        items=ctx.items,
        coverage=coverage,
        trace=trace,
    )
