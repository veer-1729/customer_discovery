from __future__ import annotations

import os

import httpx

from customer_discovery.research.search.base import SearchResult


class GoogleCseSearchProvider:
    def __init__(
        self,
        api_key: str | None = None,
        cx: str | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("GOOGLE_CSE_API_KEY", "")
        self._cx = cx or os.environ.get("GOOGLE_CSE_CX", "")
        if not self._api_key or not self._cx:
            raise ValueError("GOOGLE_CSE_API_KEY and GOOGLE_CSE_CX are required")

    def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                "https://www.googleapis.com/customsearch/v1",
                params={
                    "key": self._api_key,
                    "cx": self._cx,
                    "q": query,
                    "num": min(max_results, 10),
                },
            )
            resp.raise_for_status()
            data = resp.json()
        results: list[SearchResult] = []
        for item in data.get("items", [])[:max_results]:
            url = item.get("link")
            if not url:
                continue
            results.append(
                SearchResult(
                    title=item.get("title"),
                    url=url,
                    snippet=item.get("snippet"),
                    source="google_cse",
                    query_used=query,
                )
            )
        return results
