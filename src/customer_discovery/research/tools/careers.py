from __future__ import annotations

from customer_discovery.research.fetch import build_url
from customer_discovery.research.keywords import has_careers_signal
from customer_discovery.research.tools.base import ToolContext, fetch_page, make_item
from customer_discovery.research.tools.known_links import pick_links
from customer_discovery.research.tools.search_fallback import SearchFallbackTool


def run_careers(ctx: ToolContext) -> None:
    if _phase_a_deterministic(ctx):
        return
    if not ctx.search_enabled:
        return
    _phase_b_search(ctx)


def _phase_a_deterministic(ctx: ToolContext) -> bool:
    urls: list[str] = list(pick_links(ctx, "careers"))
    paths = ctx.cfg.get("agentic_collection", {}).get("careers_paths", [])
    if ctx.website:
        for p in paths:
            urls.append(build_url(ctx.website, p))
    seen: set[str] = set()
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        result, cache_path = fetch_page(ctx, url)
        if result.success and (has_careers_signal(result.text) or "career" in url.lower() or "job" in url.lower()):
            ctx.items.append(
                make_item(
                    ctx,
                    source_type="careers",
                    url=result.url,
                    title=result.title,
                    text_snippet=result.text,
                    raw_cache_path_str=cache_path,
                    metadata={"discovered_via": "deterministic"},
                )
            )
            return True
    return False


def _phase_b_search(ctx: ToolContext) -> None:
    cs = ctx.cfg.get("careers_search", {})
    if not cs.get("enabled", True):
        return
    templates = cs.get("queries", [])
    max_q = cs.get("max_search_queries", 8)
    max_pages = cs.get("max_pages_to_fetch", 5)
    max_results = ctx.cfg.get("search", {}).get("max_results_per_query", 5)

    fetched_urls: set[str] = set()
    for template in templates[:max_q]:
        query = template.format(company_name=ctx.company_name)
        try:
            results = SearchFallbackTool.search(query, max_results)
        except Exception as e:
            ctx.items.append(
                make_item(
                    ctx,
                    source_type="search_result",
                    success=False,
                    error=str(e),
                    metadata={"query": query},
                )
            )
            continue
        for sr in results:
            ctx.items.append(
                make_item(
                    ctx,
                    source_type="search_result",
                    url=sr.url,
                    title=sr.title,
                    text_snippet=sr.snippet or "",
                    metadata={
                        "query_used": sr.query_used,
                        "search_provider": sr.source,
                    },
                )
            )
        for sr in results:
            if sr.url in fetched_urls:
                continue
            if len(fetched_urls) >= max_pages:
                break
            fetched_urls.add(sr.url)
            result, cache_path = fetch_page(ctx, sr.url)
            if not result.success:
                continue
            if has_careers_signal(result.text) or any(
                d in sr.url.lower() for d in ("ashbyhq", "lever.co", "greenhouse", "workable", "ycombinator")
            ):
                ctx.items.append(
                    make_item(
                        ctx,
                        source_type="careers",
                        url=result.url,
                        title=result.title,
                        text_snippet=result.text,
                        raw_cache_path_str=cache_path,
                        metadata={"discovered_via": "search", "query_used": sr.query_used},
                    )
                )
                return
            ctx.items.append(
                make_item(
                    ctx,
                    source_type="fallback_page",
                    url=result.url,
                    title=result.title,
                    text_snippet=result.text[:2000],
                    raw_cache_path_str=cache_path,
                    metadata={
                        "search_query": sr.query_used,
                        "search_provider": sr.source,
                    },
                )
            )
