from __future__ import annotations

import os

import httpx

from customer_discovery.research.search.base import SearchResult


class SerpApiSearchProvider:
    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("SERPAPI_API_KEY", "")
        if not self._api_key:
            raise ValueError("SERPAPI_API_KEY is required for SerpAPI search provider")

    def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                "https://serpapi.com/search",
                params={
                    "api_key": self._api_key,
                    "engine": "google",
                    "q": query,
                    "num": max_results,
                },
            )
            resp.raise_for_status()
            data = resp.json()
        results: list[SearchResult] = []
        for item in data.get("organic_results", [])[:max_results]:
            url = item.get("link")
            if not url:
                continue
            results.append(
                SearchResult(
                    title=item.get("title"),
                    url=url,
                    snippet=item.get("snippet"),
                    source="serpapi",
                    query_used=query,
                )
            )
        return results
