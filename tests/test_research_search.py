from __future__ import annotations

from unittest.mock import patch

from customer_discovery.research.search.base import SearchResult
from customer_discovery.research.tools.search_fallback import SearchFallbackTool


class MockProvider:
    def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]:
        return [
            SearchResult(
                title="Careers",
                url="https://jobs.example.com",
                snippet="Join us",
                source="mock",
                query_used=query,
            )
        ]


def test_search_fallback_tool_delegates():
    SearchFallbackTool._provider = MockProvider()
    SearchFallbackTool._cfg = {"search": {"max_results_per_query": 5}}
    results = SearchFallbackTool.search("Acme careers", 3)
    assert len(results) == 1
    assert results[0].query_used == "Acme careers"
