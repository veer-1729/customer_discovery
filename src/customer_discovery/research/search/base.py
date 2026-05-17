from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel


class SearchResult(BaseModel):
    title: str | None = None
    url: str
    snippet: str | None = None
    source: str
    query_used: str


class SearchProvider(Protocol):
    def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]: ...
