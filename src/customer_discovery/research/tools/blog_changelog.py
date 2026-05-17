from __future__ import annotations

from customer_discovery.research.fetch import build_url
from customer_discovery.research.tools.base import ToolContext, fetch_page, make_item
from customer_discovery.research.tools.known_links import pick_links


def run_blog_changelog(ctx: ToolContext) -> None:
    urls = list(pick_links(ctx, "blog"))
    paths = ctx.cfg.get("agentic_collection", {}).get("blog_paths", [])
    if ctx.website:
        for p in paths:
            urls.append(build_url(ctx.website, p))
    seen: set[str] = set()
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        result, cache_path = fetch_page(ctx, url)
        if not result.success:
            continue
        st = "changelog" if "changelog" in url.lower() or "changelog" in (result.title or "").lower() else "blog"
        ctx.items.append(
            make_item(
                ctx,
                source_type=st,  # type: ignore[arg-type]
                url=result.url,
                title=result.title,
                text_snippet=result.text,
                raw_cache_path_str=cache_path,
            )
        )
        return
