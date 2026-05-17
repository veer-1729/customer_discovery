from __future__ import annotations

import os

import httpx

from customer_discovery.research.search.base import SearchResult


class TavilySearchProvider:
    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("TAVILY_API_KEY", "")
        if not self._api_key:
            raise ValueError("TAVILY_API_KEY is required for Tavily search provider")

    def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self._api_key,
                    "query": query,
                    "max_results": max_results,
                    "include_answer": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
        results: list[SearchResult] = []
        for item in data.get("results", [])[:max_results]:
            url = item.get("url")
            if not url:
                continue
            results.append(
                SearchResult(
                    title=item.get("title"),
                    url=url,
                    snippet=item.get("content") or item.get("snippet"),
                    source="tavily",
                    query_used=query,
                )
            )
        return results
