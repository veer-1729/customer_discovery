from __future__ import annotations

from pathlib import Path
from typing import Any

from customer_discovery.research.search.base import SearchProvider, SearchResult
from customer_discovery.research.search.budget import CreditAwareSearchProvider
from customer_discovery.research.search.factory import DisabledSearchProvider, get_search_provider


class SearchFallbackTool:
    _provider: SearchProvider | None = None
    _cfg: dict[str, Any] | None = None
    _enabled: bool = True
    _state_dir: Path | None = None
    _force_search: bool = False

    @classmethod
    def configure(
        cls,
        cfg: dict[str, Any],
        *,
        enabled: bool = True,
        state_dir: Path | None = None,
        force_search: bool = False,
    ) -> None:
        cls._cfg = cfg
        cls._enabled = enabled
        cls._state_dir = state_dir
        cls._force_search = force_search
        cls._provider = cls._build_provider(cfg, enabled=enabled)

    @classmethod
    def _build_provider(cls, cfg: dict[str, Any], *, enabled: bool) -> SearchProvider:
        if not enabled or not cfg.get("search", {}).get("enabled", True):
            return DisabledSearchProvider()
        fallbacks = cfg.get("search", {}).get("fallback_providers") or []
        if fallbacks or cls._state_dir is not None:
            state_path = (cls._state_dir / "search_state.json") if cls._state_dir else None
            return CreditAwareSearchProvider(
                cfg,
                state_path=state_path,
                force_search=cls._force_search,
            )
        return get_search_provider(cfg, enabled=enabled)

    @classmethod
    def search(cls, query: str, max_results: int) -> list[SearchResult]:
        if cls._provider is None:
            if cls._cfg is None:
                raise RuntimeError("SearchFallbackTool.configure() must be called first")
            cls._provider = cls._build_provider(cls._cfg, enabled=cls._enabled)
        cfg = cls._cfg or {}
        cap = cfg.get("search", {}).get("max_results_per_query", max_results)
        return cls._provider.search(query, max_results=min(max_results, cap))

    @classmethod
    def search_exhausted(cls) -> bool:
        if isinstance(cls._provider, CreditAwareSearchProvider):
            return cls._provider.exhausted
        return False
