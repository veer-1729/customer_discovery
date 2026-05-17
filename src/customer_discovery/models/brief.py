from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    signal: str
    url: str | None = None
    snippet: str | None = None


class IcpFit(BaseModel):
    fit: bool | None = None
    reasoning: str | None = None


class ResearchBrief(BaseModel):
    """Part 2 output schema (stub — generation not implemented yet)."""

    company_id: str
    summary: str | None = None
    icp_fit: IcpFit = Field(default_factory=IcpFit)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    disqualifiers: list[str] = Field(default_factory=list)
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] | None = None
    fit_score: float | None = Field(default=None, ge=0, le=100)
    sources_checked: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)
