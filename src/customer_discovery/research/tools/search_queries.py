from __future__ import annotations

from customer_discovery.research.search_relevance import filter_search_results, format_search_query
from customer_discovery.research.tools.base import ToolContext
from customer_discovery.research.tools.search_fallback import SearchFallbackTool
from customer_discovery.research.search.base import SearchResult


def run_filtered_search(
    ctx: ToolContext,
    template: str,
    max_results: int,
) -> list[SearchResult]:
    query = format_search_query(
        template,
        company_name=ctx.company_name,
        website=ctx.website,
        raw=ctx.company.raw,
    )
    if not query:
        return []
    try:
        results = SearchFallbackTool.search(query, max_results)
    except Exception:
        return []
    rel = search_context_from_ctx(ctx)
    return filter_search_results(results, **rel)


def search_context_from_ctx(ctx: ToolContext) -> dict[str, str | None]:
    from customer_discovery.research.search_relevance import search_context_from_company

    return search_context_from_company(ctx.company)
