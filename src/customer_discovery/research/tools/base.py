from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from customer_discovery.models.company import CompanyRecord
from customer_discovery.models.evidence import EvidenceItem, new_evidence_id
from customer_discovery.research.cache import raw_cache_path, read_cached, write_cached
from customer_discovery.research.fetch import FetchResult, PageFetcher


@dataclass
class ToolContext:
    company: CompanyRecord
    cfg: dict[str, Any]
    raw_cache_dir: Path
    fetcher: PageFetcher
    search_enabled: bool = True
    force_refetch: bool = False
    items: list[EvidenceItem] = field(default_factory=list)
    discovered_links: dict[str, list[str]] = field(default_factory=dict)
    tool_calls: int = 0

    @property
    def company_id(self) -> str:
        return self.company.id

    @property
    def company_name(self) -> str:
        return self.company.name

    @property
    def website(self) -> str | None:
        return str(self.company.website) if self.company.website else None


def make_item(
    ctx: ToolContext,
    *,
    source_type: str,
    url: str | None = None,
    title: str | None = None,
    text_snippet: str = "",
    success: bool = True,
    error: str | None = None,
    raw_cache_path_str: str | None = None,
    metadata: dict | None = None,
) -> EvidenceItem:
    return EvidenceItem(
        id=new_evidence_id(),
        company_id=ctx.company_id,
        source_type=source_type,  # type: ignore[arg-type]
        url=url,
        title=title,
        text_snippet=text_snippet[:8000],
        raw_cache_path=raw_cache_path_str,
        success=success,
        error=error,
        metadata=metadata or {},
    )


def fetch_page(
    ctx: ToolContext,
    url: str,
) -> tuple[FetchResult, str | None]:
    ctx.tool_calls += 1
    cache_path = raw_cache_path(ctx.raw_cache_dir, ctx.company_id, url)
    if not ctx.force_refetch:
        cached = read_cached(cache_path)
        if cached:
            from customer_discovery.research.fetch import extract_text, extract_title

            return (
                FetchResult(
                    url=url,
                    success=True,
                    title=extract_title(cached),
                    text=extract_text(cached),
                    html=cached,
                ),
                str(cache_path),
            )
    result = ctx.fetcher.fetch(url)
    path_str = None
    if result.success and result.html:
        path_str = write_cached(cache_path, result.html)
    return result, path_str
