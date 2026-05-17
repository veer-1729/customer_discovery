from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

SourceType = Literal[
    "seed_metadata",
    "homepage",
    "careers",
    "docs",
    "status",
    "blog",
    "changelog",
    "github",
    "search_result",
    "fallback_page",
]

ConfidenceLevel = Literal["low", "medium", "high"]


def new_evidence_id() -> str:
    return f"ev_{uuid.uuid4().hex[:12]}"


class EvidenceItem(BaseModel):
    id: str
    company_id: str
    source_type: SourceType
    url: str | None = None
    title: str | None = None
    text_snippet: str = ""
    raw_cache_path: str | None = None
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    success: bool = True
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResearchTrace(BaseModel):
    probes_attempted: list[str] = Field(default_factory=list)
    urls_attempted: list[str] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)
    cache_hits: int = 0
    tool_calls: int = 0


class EvidenceCoverage(BaseModel):
    homepage_found: bool = False
    careers_found: bool = False
    docs_found: bool = False
    status_found: bool = False
    blog_or_changelog_found: bool = False
    github_found: bool = False
    seed_metadata_found: bool = False
    fallback_search_used: bool = False
    total_successful_sources: int = 0
    source_diversity_score: float = 0.0
    confidence_cap: ConfidenceLevel = "low"


class EvidenceBundle(BaseModel):
    company_id: str
    company_name: str
    website: str | None = None
    source: str = ""
    items: list[EvidenceItem] = Field(default_factory=list)
    coverage: EvidenceCoverage = Field(default_factory=EvidenceCoverage)
    trace: ResearchTrace = Field(default_factory=ResearchTrace)


SOURCE_TYPES_FOR_DIVERSITY = frozenset(
    {"homepage", "careers", "docs", "status", "blog", "changelog", "github", "seed_metadata"}
)


def compute_coverage(items: list[EvidenceItem]) -> EvidenceCoverage:
    successful = [i for i in items if i.success]
    by_type: dict[str, EvidenceItem] = {}
    for item in successful:
        if item.source_type not in by_type:
            by_type[item.source_type] = item

    homepage = "homepage" in by_type
    careers = "careers" in by_type
    docs = "docs" in by_type
    status = "status" in by_type
    blog = "blog" in by_type or "changelog" in by_type
    github = "github" in by_type
    seed = "seed_metadata" in by_type
    fallback_search = any(
        i.source_type in ("search_result", "fallback_page") for i in successful
    )

    types_present = {
        t
        for t in by_type
        if t in SOURCE_TYPES_FOR_DIVERSITY or t in ("blog", "changelog")
    }
    diversity = len(types_present) / max(len(SOURCE_TYPES_FOR_DIVERSITY), 1)

    cap = _confidence_cap(
        homepage=homepage,
        careers=careers,
        docs=docs,
        seed=seed,
        types_count=len(types_present),
        fallback_only=_fallback_only(successful),
    )

    return EvidenceCoverage(
        homepage_found=homepage,
        careers_found=careers,
        docs_found=docs,
        status_found=status,
        blog_or_changelog_found=blog,
        github_found=github,
        seed_metadata_found=seed,
        fallback_search_used=fallback_search,
        total_successful_sources=len({i.source_type for i in successful}),
        source_diversity_score=round(diversity, 3),
        confidence_cap=cap,
    )


def _fallback_only(successful: list[EvidenceItem]) -> bool:
    core = [i for i in successful if i.source_type in SOURCE_TYPES_FOR_DIVERSITY]
    if not core:
        return bool(successful)
    return all(i.source_type in ("search_result", "fallback_page", "seed_metadata") for i in core)


def _confidence_cap(
    *,
    homepage: bool,
    careers: bool,
    docs: bool,
    seed: bool,
    types_count: int,
    fallback_only: bool,
) -> ConfidenceLevel:
    if fallback_only and not (homepage or careers or docs):
        return "medium"
    if homepage and careers and docs:
        return "high"
    if types_count >= 3:
        return "high"
    if types_count >= 2:
        return "medium"
    if homepage and not careers and not docs:
        return "low"
    if seed and not homepage:
        return "low"
    return "low"


def cap_confidence(requested: ConfidenceLevel, coverage: EvidenceCoverage) -> ConfidenceLevel:
    order = {"low": 0, "medium": 1, "high": 2}
    cap = coverage.confidence_cap
    if order[requested] <= order[cap]:
        return requested
    return cap
