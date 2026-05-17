from __future__ import annotations

from customer_discovery.research.fetch import build_url, status_subdomain_url
from customer_discovery.research.tools.base import ToolContext, fetch_page, make_item
from customer_discovery.research.tools.known_links import pick_links


def run_status_page(ctx: ToolContext) -> None:
    urls = list(pick_links(ctx, "status"))
    if ctx.website:
        sub = status_subdomain_url(ctx.website)
        if sub:
            urls.insert(0, sub)
        for p in ctx.cfg.get("agentic_collection", {}).get("status_paths", ["/status"]):
            urls.append(build_url(ctx.website, p))
    seen: set[str] = set()
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        result, cache_path = fetch_page(ctx, url)
        if result.success:
            ctx.items.append(
                make_item(
                    ctx,
                    source_type="status",
                    url=result.url,
                    title=result.title,
                    text_snippet=result.text,
                    raw_cache_path_str=cache_path,
                )
            )
            return
