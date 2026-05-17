from __future__ import annotations

import os

import httpx

from customer_discovery.research.search.base import SearchResult


class BraveSearchProvider:
    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("BRAVE_SEARCH_API_KEY", "")
        if not self._api_key:
            raise ValueError("BRAVE_SEARCH_API_KEY is required for Brave search provider")

    def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"X-Subscription-Token": self._api_key},
                params={"q": query, "count": max_results},
            )
            resp.raise_for_status()
            data = resp.json()
        results: list[SearchResult] = []
        for item in data.get("web", {}).get("results", [])[:max_results]:
            url = item.get("url")
            if not url:
                continue
            results.append(
                SearchResult(
                    title=item.get("title"),
                    url=url,
                    snippet=item.get("description"),
                    source="brave",
                    query_used=query,
                )
            )
        return results
