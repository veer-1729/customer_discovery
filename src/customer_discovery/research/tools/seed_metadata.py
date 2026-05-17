from __future__ import annotations

import json

from customer_discovery.research.tools.base import ToolContext, make_item


def run_seed_metadata(ctx: ToolContext) -> None:
    c = ctx.company
    parts = []
    if c.description:
        parts.append(c.description)
    if c.industry:
        parts.append("Industries: " + ", ".join(c.industry))
    if c.batch:
        parts.append(f"Batch: {c.batch}")
    if c.team:
        parts.append(f"Team size (listed): {len(c.team)}")
    raw_snip = json.dumps(c.raw, default=str)[:4000] if c.raw else ""
    text = "\n".join(parts) + ("\n" + raw_snip if raw_snip else "")
    ctx.items.append(
        make_item(
            ctx,
            source_type="seed_metadata",
            url=str(c.source_url) if c.source_url else None,
            title=f"{c.source} seed metadata",
            text_snippet=text or "(no seed description)",
            metadata={"source": c.source, "program": c.program},
        )
    )
