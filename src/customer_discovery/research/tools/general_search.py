from __future__ import annotations

from customer_discovery.research.keywords import has_careers_signal, has_docs_signal
from customer_discovery.research.tools.base import ToolContext, fetch_page, make_item
from customer_discovery.research.tools.search_queries import run_filtered_search


def run_agent_search_fallback(ctx: ToolContext, coverage_types: int) -> None:
    """Global weak-coverage search — runs after deterministic tools."""
    if not ctx.search_enabled:
        return
    threshold = ctx.cfg.get("agentic_collection", {}).get("weak_coverage_threshold", 2)
    if coverage_types >= threshold:
        return
    search_cfg = ctx.cfg.get("search", {})
    max_q = search_cfg.get("max_queries_per_company", 5)
    max_pages = search_cfg.get("max_pages_fetched_from_results", 5)
    max_results = search_cfg.get("max_results_per_query", 5)
    templates = search_cfg.get("general_queries", [])
    fetched: set[str] = set()
    queries_run = 0
    for template in templates:
        if queries_run >= max_q:
            break
        results = run_filtered_search(ctx, template, max_results)
        queries_run += 1
        if not results:
            continue
        for sr in results:
            ctx.items.append(
                make_item(
                    ctx,
                    source_type="search_result",
                    url=sr.url,
                    title=sr.title,
                    text_snippet=sr.snippet or "",
                    metadata={"query_used": sr.query_used, "search_provider": sr.source},
                )
            )
        for sr in results:
            if sr.url in fetched or len(fetched) >= max_pages:
                continue
            fetched.add(sr.url)
            result, cache_path = fetch_page(ctx, sr.url)
            if not result.success:
                continue
            st = "fallback_page"
            if has_careers_signal(result.text):
                st = "careers"
            elif has_docs_signal(result.text):
                st = "docs"
            ctx.items.append(
                make_item(
                    ctx,
                    source_type=st,  # type: ignore[arg-type]
                    url=result.url,
                    title=result.title,
                    text_snippet=result.text[:4000],
                    raw_cache_path_str=cache_path,
                    metadata={"search_query": sr.query_used, "agent_fallback": True},
                )
            )
