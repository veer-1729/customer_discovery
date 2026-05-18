from __future__ import annotations

import json
from pathlib import Path
import httpx

from customer_discovery.research.search.base import SearchResult
from customer_discovery.research.search.budget import CreditAwareSearchProvider, is_quota_error
from customer_discovery.research.tools.search_fallback import SearchFallbackTool


def test_is_quota_error_http_429():
    req = httpx.Request("GET", "https://api.tavily.com")
    resp = httpx.Response(429, request=req)
    err = httpx.HTTPStatusError("rate limit", request=req, response=resp)
    assert is_quota_error(err)


class QuotaProvider:
    def __init__(self) -> None:
        self.calls = 0

    def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]:
        self.calls += 1
        req = httpx.Request("GET", "https://example.com")
        resp = httpx.Response(429, request=req)
        raise httpx.HTTPStatusError("quota exceeded", request=req, response=resp)


class OkProvider:
    def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]:
        return [
            SearchResult(
                title="Hit",
                url="https://acme.com/careers",
                snippet="jobs",
                source="ok",
                query_used=query,
            )
        ]


def test_tavily_quota_falls_through_to_serpapi(tmp_path: Path):
    state = tmp_path / "search_state.json"
    cfg = {
        "search": {
            "enabled": True,
            "provider": "tavily",
            "fallback_providers": ["serpapi"],
        }
    }
    provider = CreditAwareSearchProvider(cfg, state_path=state)
    provider._providers = {"tavily": QuotaProvider(), "serpapi": OkProvider()}
    provider._active_order = ["tavily", "serpapi"]

    results = provider.search("acme careers", max_results=3)
    assert len(results) == 1
    assert results[0].url == "https://acme.com/careers"
    assert "tavily" in provider._provider_errors


def test_all_providers_exhausted_writes_state_and_skips(tmp_path: Path):
    state = tmp_path / "search_state.json"
    cfg = {
        "search": {
            "enabled": True,
            "provider": "tavily",
            "fallback_providers": ["serpapi"],
        }
    }
    provider = CreditAwareSearchProvider(cfg, state_path=state)
    provider._providers = {"tavily": QuotaProvider(), "serpapi": QuotaProvider()}
    provider._active_order = ["tavily", "serpapi"]

    assert provider.search("q1", max_results=1) == []
    assert state.exists()
    data = json.loads(state.read_text())
    assert data["exhausted"] is True

    assert provider.search("q2", max_results=1) == []
    assert provider._providers["tavily"].calls == 1
    assert provider._providers["serpapi"].calls == 1


def test_resume_loads_exhausted_state(tmp_path: Path):
    state = tmp_path / "search_state.json"
    state.write_text(
        json.dumps({"exhausted": True, "providers": {"tavily": "quota"}}),
        encoding="utf-8",
    )
    cfg = {"search": {"enabled": True, "provider": "tavily", "fallback_providers": ["serpapi"]}}
    provider = CreditAwareSearchProvider(cfg, state_path=state)
    assert provider.exhausted
    assert provider.search("anything", max_results=5) == []


def test_search_fallback_tool_uses_budget_with_state_dir(tmp_path: Path):
    SearchFallbackTool.configure(
        {"search": {"enabled": True, "provider": "tavily", "fallback_providers": ["serpapi"]}},
        state_dir=tmp_path,
    )
    assert isinstance(SearchFallbackTool._provider, CreditAwareSearchProvider)
