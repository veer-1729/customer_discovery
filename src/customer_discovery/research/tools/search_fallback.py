from __future__ import annotations

from typing import Any

from customer_discovery.research.search.base import SearchProvider, SearchResult
from customer_discovery.research.search.factory import get_search_provider


class SearchFallbackTool:
    _provider: SearchProvider | None = None
    _cfg: dict[str, Any] | None = None
    _enabled: bool = True

    @classmethod
    def configure(cls, cfg: dict[str, Any], *, enabled: bool = True) -> None:
        cls._cfg = cfg
        cls._enabled = enabled
        cls._provider = get_search_provider(cfg, enabled=enabled)

    @classmethod
    def search(cls, query: str, max_results: int) -> list[SearchResult]:
        if cls._provider is None:
            if cls._cfg is None:
                raise RuntimeError("SearchFallbackTool.configure() must be called first")
            cls._provider = get_search_provider(cls._cfg, enabled=cls._enabled)
        cfg = cls._cfg or {}
        cap = cfg.get("search", {}).get("max_results_per_query", max_results)
        return cls._provider.search(query, max_results=min(max_results, cap))
