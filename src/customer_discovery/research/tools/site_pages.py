from __future__ import annotations

import re

from customer_discovery.research.fetch import build_url, fetch_dedup_key
from customer_discovery.research.tools.base import ToolContext, fetch_page, make_item
from customer_discovery.research.tools.known_links import LINK_PATTERNS, pick_links

_SECTION_FROM_URL = re.compile(
    r"(team|pricing|features?|contact|faq|services?|blog|careers?|docs?)",
    re.I,
)


def _infer_section(url: str) -> str:
    parsed_fragment = ""
    if "#" in url:
        parsed_fragment = url.split("#", 1)[-1].lower()
        if parsed_fragment:
            return parsed_fragment[:40]
    m = _SECTION_FROM_URL.search(url)
    return m.group(1).lower() if m else "site"


def _collect_candidate_urls(ctx: ToolContext) -> list[tuple[str, str]]:
    """Return (url, discovered_via) pairs in priority order."""
    ac = ctx.cfg.get("agentic_collection", {})
    paths: list[str] = list(ac.get("site_paths", []))
    candidates: list[tuple[str, str]] = []

    for kind in LINK_PATTERNS:
        for url in pick_links(ctx, kind):
            candidates.append((url, "nav_link"))

    if ctx.website:
        for path in paths:
            candidates.append((build_url(ctx.website, path), "site_path"))

    return candidates


def run_site_pages(ctx: ToolContext) -> None:
    """Probe common marketing paths and nav links (team, pricing, /#sections, etc.)."""
    ac = ctx.cfg.get("agentic_collection", {})
    max_fetches = int(ac.get("max_site_page_fetches", 8))
    min_chars = int(ac.get("min_site_page_chars", 80))

    already_fetched = {
        fetch_dedup_key(i.url)
        for i in ctx.items
        if i.success and i.url
    }
    seen_keys: set[tuple[str, str, str]] = set(already_fetched)
    fetched = 0

    for url, via in _collect_candidate_urls(ctx):
        if fetched >= max_fetches:
            break
        key = fetch_dedup_key(url)
        if key in seen_keys:
            continue
        seen_keys.add(key)

        result, cache_path = fetch_page(ctx, url)
        fetched += 1
        if not result.success:
            continue
        if len(result.text.strip()) < min_chars:
            continue
        # Skip near-duplicate of homepage body when fragment-only SPA shell
        homepage = next(
            (i for i in ctx.items if i.source_type == "homepage" and i.success),
            None,
        )
        if homepage and key == fetch_dedup_key(homepage.url or ""):
            if len(result.text) < len(homepage.text_snippet) + 50:
                continue

        section = _infer_section(url)
        ctx.items.append(
            make_item(
                ctx,
                source_type="fallback_page",
                url=result.url,
                title=result.title,
                text_snippet=result.text,
                raw_cache_path_str=cache_path,
                metadata={
                    "discovered_via": via,
                    "site_section": section,
                },
            )
        )
