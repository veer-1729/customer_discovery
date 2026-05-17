from __future__ import annotations

import json
import os

from customer_discovery.research.search.base import SearchResult


class OpenAIWebSearchProvider:
    """Uses OpenAI Responses API with web_search tool when available."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not self._api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI web search provider")

    def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError("openai package required for OpenAI web search") from e

        client = OpenAI(api_key=self._api_key)
        resp = client.responses.create(
            model="gpt-4o-mini",
            tools=[{"type": "web_search_preview"}],
            input=f"Search the web for: {query}. Return up to {max_results} results as JSON array with title, url, snippet fields only.",
        )
        text = ""
        for item in resp.output:
            if hasattr(item, "content"):
                for c in item.content:
                    if hasattr(c, "text"):
                        text += c.text
        try:
            start = text.find("[")
            end = text.rfind("]") + 1
            rows = json.loads(text[start:end]) if start >= 0 else []
        except json.JSONDecodeError:
            rows = []

        results: list[SearchResult] = []
        for row in rows[:max_results]:
            url = row.get("url")
            if url:
                results.append(
                    SearchResult(
                        title=row.get("title"),
                        url=url,
                        snippet=row.get("snippet"),
                        source="openai",
                        query_used=query,
                    )
                )
        return results
