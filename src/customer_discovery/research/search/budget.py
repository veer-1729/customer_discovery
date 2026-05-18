from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from customer_discovery.research.search.base import SearchProvider, SearchResult
from customer_discovery.research.search.factory import DisabledSearchProvider, get_search_provider

logger = logging.getLogger(__name__)

_QUOTA_STATUS = {402, 403, 429}
_QUOTA_KEYWORDS = ("quota", "credit", "limit", "insufficient", "exceeded", "billing")


def is_quota_error(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        if exc.response.status_code in _QUOTA_STATUS:
            return True
        try:
            body = exc.response.text.lower()
        except Exception:
            body = ""
        return any(k in body for k in _QUOTA_KEYWORDS)
    msg = str(exc).lower()
    return any(k in msg for k in _QUOTA_KEYWORDS)


def _provider_names(cfg: dict[str, Any]) -> list[str]:
    search_cfg = cfg.get("search", {})
    primary = (search_cfg.get("provider") or "tavily").lower()
    fallbacks = [p.lower() for p in search_cfg.get("fallback_providers", [])]
    names: list[str] = []
    for name in [primary, *fallbacks]:
        if name and name not in names:
            names.append(name)
    return names


class CreditAwareSearchProvider:
    """Tavily → SerpAPI (config order); disable all search when credits exhausted."""

    def __init__(
        self,
        cfg: dict[str, Any],
        *,
        state_path: Path | None = None,
        force_search: bool = False,
    ) -> None:
        self._cfg = cfg
        self._state_path = state_path
        self._force_search = force_search
        self._exhausted = False
        self._exhausted_logged = False
        self._provider_errors: dict[str, str] = {}
        self._providers: dict[str, SearchProvider] = {}
        self._active_order: list[str] = []

        if state_path and state_path.exists() and not force_search:
            try:
                data = json.loads(state_path.read_text(encoding="utf-8"))
                if data.get("exhausted"):
                    self._exhausted = True
                    self._provider_errors = dict(data.get("providers", {}))
            except (json.JSONDecodeError, OSError):
                pass

        if not self._exhausted:
            for name in _provider_names(cfg):
                sub_cfg = {**cfg, "search": {**cfg.get("search", {}), "provider": name}}
                try:
                    provider = get_search_provider(sub_cfg, enabled=True)
                    if isinstance(provider, DisabledSearchProvider):
                        continue
                    self._providers[name] = provider
                    self._active_order.append(name)
                except ValueError:
                    continue

    @property
    def exhausted(self) -> bool:
        return self._exhausted

    def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]:
        if self._exhausted and not self._force_search:
            return []

        for name in self._active_order:
            if name in self._provider_errors:
                continue
            provider = self._providers.get(name)
            if not provider:
                continue
            try:
                return provider.search(query, max_results=max_results)
            except Exception as exc:
                if is_quota_error(exc):
                    reason = str(exc)[:200]
                    self._provider_errors[name] = reason
                    logger.warning(
                        "Search provider %s exhausted (%s); trying next",
                        name,
                        exc,
                    )
                    continue
                logger.warning("Search provider %s failed: %s", name, exc)
                return []

        self._mark_exhausted()
        return []

    def _mark_exhausted(self) -> None:
        if self._exhausted:
            return
        self._exhausted = True
        if not self._exhausted_logged:
            logger.warning(
                "All search providers exhausted (%s). "
                "Further queries will skip web search; deterministic evidence continues.",
                ", ".join(self._provider_errors.keys()) or "none configured",
            )
            self._exhausted_logged = True
        if self._state_path:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "exhausted": True,
                "exhausted_at": datetime.now(timezone.utc).isoformat(),
                "providers": self._provider_errors,
            }
            self._state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
