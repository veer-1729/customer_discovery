from __future__ import annotations

from customer_discovery.research.fetch import build_url
from customer_discovery.research.keywords import has_docs_signal
from customer_discovery.research.tools.base import ToolContext, fetch_page, make_item
from customer_discovery.research.tools.known_links import pick_links


def run_docs(ctx: ToolContext) -> None:
    urls = list(pick_links(ctx, "docs"))
    paths = ctx.cfg.get("agentic_collection", {}).get("docs_paths", [])
    if ctx.website:
        for p in paths:
            urls.append(build_url(ctx.website, p))
    seen: set[str] = set()
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        result, cache_path = fetch_page(ctx, url)
        if result.success and (has_docs_signal(result.text) or "doc" in url.lower() or "api" in url.lower()):
            ctx.items.append(
                make_item(
                    ctx,
                    source_type="docs",
                    url=result.url,
                    title=result.title,
                    text_snippet=result.text,
                    raw_cache_path_str=cache_path,
                )
            )
            return
