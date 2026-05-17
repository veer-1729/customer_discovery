from __future__ import annotations

from customer_discovery.research.tools.base import ToolContext, fetch_page, make_item
from customer_discovery.research.tools.known_links import pick_links


def run_github(ctx: ToolContext) -> None:
    urls = list(pick_links(ctx, "github"))
    if not urls and ctx.company.links.github:
        urls = [str(ctx.company.links.github)]
    for url in urls[:2]:
        if "github.com" not in url:
            continue
        result, cache_path = fetch_page(ctx, url)
        if result.success:
            ctx.items.append(
                make_item(
                    ctx,
                    source_type="github",
                    url=result.url,
                    title=result.title,
                    text_snippet=result.text,
                    raw_cache_path_str=cache_path,
                )
            )
            return
