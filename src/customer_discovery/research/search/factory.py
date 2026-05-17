from __future__ import annotations

import logging
from typing import Any

from customer_discovery.research.search.base import SearchProvider
from customer_discovery.research.search.serpapi import SerpApiSearchProvider
from customer_discovery.research.search.tavily import TavilySearchProvider

logger = logging.getLogger(__name__)


class DisabledSearchProvider:
    def search(self, query: str, *, max_results: int = 5) -> list:
        return []


def get_search_provider(cfg: dict[str, Any], *, enabled: bool = True) -> SearchProvider:
    search_cfg = cfg.get("search", {})
    if not enabled or not search_cfg.get("enabled", True):
        return DisabledSearchProvider()

    provider = (search_cfg.get("provider") or "tavily").lower()
    try:
        if provider == "tavily":
            return TavilySearchProvider()
        if provider == "serpapi":
            return SerpApiSearchProvider()
        if provider == "brave":
            from customer_discovery.research.search.brave import BraveSearchProvider

            return BraveSearchProvider()
        if provider == "bing":
            from customer_discovery.research.search.bing import BingSearchProvider

            return BingSearchProvider()
        if provider in ("google_cse", "google"):
            from customer_discovery.research.search.google_cse import GoogleCseSearchProvider

            return GoogleCseSearchProvider()
        if provider == "openai":
            from customer_discovery.research.search.openai_web import OpenAIWebSearchProvider

            return OpenAIWebSearchProvider()
        raise ValueError(f"Unknown search provider: {provider}")
    except ValueError as e:
        logger.warning("Search provider unavailable (%s); search fallback disabled", e)
        return DisabledSearchProvider()
