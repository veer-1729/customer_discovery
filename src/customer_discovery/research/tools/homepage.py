from __future__ import annotations

from customer_discovery.research.tools.base import ToolContext, fetch_page, make_item


def run_homepage(ctx: ToolContext) -> None:
    if not ctx.website:
        ctx.items.append(
            make_item(
                ctx,
                source_type="homepage",
                success=False,
                error="no website on record",
            )
        )
        return
    result, cache_path = fetch_page(ctx, ctx.website)
    if not result.success:
        ctx.items.append(
            make_item(
                ctx,
                source_type="homepage",
                url=ctx.website,
                success=False,
                error=result.error,
            )
        )
        return
    ctx.items.append(
        make_item(
            ctx,
            source_type="homepage",
            url=result.url,
            title=result.title,
            text_snippet=result.text,
            raw_cache_path_str=cache_path,
        )
    )
