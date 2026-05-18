from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

_SEASONS_LEGACY = ("Winter", "Summer")
_SEASONS_MODERN = ("Winter", "Summer", "Spring", "Fall")
_MODERN_BATCHES_FROM_YEAR = 2025


def yc_batches_for_year_range(start: int, end: int) -> list[str]:
    """Build Algolia batch facet labels for inclusive year range (newest first)."""
    batches: list[str] = []
    for year in range(end, start - 1, -1):
        seasons = _SEASONS_MODERN if year >= _MODERN_BATCHES_FROM_YEAR else _SEASONS_LEGACY
        for season in seasons:
            batches.append(f"{season} {year}")
    return batches


@dataclass
class YCFilterConfig:
    batches: list[str] = field(default_factory=list)
    regions: list[str] = field(default_factory=list)
    industries: list[str] = field(default_factory=list)
    statuses: list[str] = field(default_factory=list)
    team_size_min: int | None = None
    team_size_max: int | None = None
    query: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> YCFilterConfig:
        f = data.get("filters", data)
        return cls(
            batches=list(f.get("batches") or []),
            regions=list(f.get("regions") or []),
            industries=list(f.get("industries") or []),
            statuses=list(f.get("statuses") or f.get("status") and [f["status"]] or []),
            team_size_min=f.get("team_size_min"),
            team_size_max=f.get("team_size_max"),
            query=str(f.get("query") or ""),
        )

    @classmethod
    def from_url(cls, url: str) -> YCFilterConfig:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query, keep_blank_values=False)
        batches = [unquote(b) for b in qs.get("batch", [])]
        regions = [unquote(r) for r in qs.get("regions", [])]
        industries = [unquote(i) for i in qs.get("industry", [])]
        statuses = [unquote(s) for s in qs.get("status", [])]

        team_min, team_max = None, None
        if "team_size" in qs:
            raw = qs["team_size"][0]
            try:
                arr = json.loads(unquote(raw))
                if isinstance(arr, list) and len(arr) >= 2:
                    team_min, team_max = int(arr[0]), int(arr[1])
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

        return cls(
            batches=batches,
            regions=regions,
            industries=industries,
            statuses=statuses,
            team_size_min=team_min,
            team_size_max=team_max,
            query="",
        )

    def merge_overrides(
        self,
        *,
        batches: list[str] | None = None,
        regions: list[str] | None = None,
        industries: list[str] | None = None,
        statuses: list[str] | None = None,
        team_size: tuple[int, int] | None = None,
        query: str | None = None,
    ) -> YCFilterConfig:
        cfg = YCFilterConfig(
            batches=list(self.batches),
            regions=list(self.regions),
            industries=list(self.industries),
            statuses=list(self.statuses),
            team_size_min=self.team_size_min,
            team_size_max=self.team_size_max,
            query=self.query,
        )
        if batches:
            cfg.batches = batches
        if regions:
            cfg.regions = regions
        if industries:
            cfg.industries = industries
        if statuses:
            cfg.statuses = statuses
        if team_size is not None:
            cfg.team_size_min, cfg.team_size_max = team_size
        if query is not None:
            cfg.query = query
        return cfg

    def build_algolia_params(self) -> dict[str, str]:
        """Build urlencoded Algolia query params (facetFilters, numericFilters, query)."""
        facet_groups: list[list[str] | str] = []

        if self.batches:
            facet_groups.append([f"batch:{b}" for b in self.batches])
        if self.regions:
            facet_groups.append([f"regions:{r}" for r in self.regions])
        if self.industries:
            facet_groups.append([f"industries:{i}" for i in self.industries])
        if self.statuses:
            facet_groups.append([f"status:{s}" for s in self.statuses])

        params: dict[str, str] = {
            "query": self.query,
            "hitsPerPage": "1000",
            "facets": json.dumps(
                [
                    "batch",
                    "industries",
                    "subindustry",
                    "status",
                    "regions",
                    "top_company",
                    "isHiring",
                    "nonprofit",
                    "tags",
                ]
            ),
            "maxValuesPerFacet": "1000",
            "tagFilters": "",
        }

        if facet_groups:
            params["facetFilters"] = json.dumps(facet_groups)

        numeric: list[str] = []
        if self.team_size_min is not None:
            numeric.append(f"team_size>={self.team_size_min}")
        if self.team_size_max is not None:
            numeric.append(f"team_size<={self.team_size_max}")
        if numeric:
            params["numericFilters"] = json.dumps(numeric)

        return params

    def with_single_batch(self, batch: str) -> YCFilterConfig:
        return YCFilterConfig(
            batches=[batch],
            regions=list(self.regions),
            industries=list(self.industries),
            statuses=list(self.statuses),
            team_size_min=self.team_size_min,
            team_size_max=self.team_size_max,
            query=self.query,
        )

    def with_single_region(self, region: str) -> YCFilterConfig:
        return YCFilterConfig(
            batches=list(self.batches),
            regions=[region],
            industries=list(self.industries),
            statuses=list(self.statuses),
            team_size_min=self.team_size_min,
            team_size_max=self.team_size_max,
            query=self.query,
        )
