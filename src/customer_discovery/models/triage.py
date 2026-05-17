from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from customer_discovery.models.evidence import ConfidenceLevel
from customer_discovery.models.signals import EvidenceBackedSignal

FitLabel = Literal["skip", "maybe", "strong_candidate", "needs_review"]


class TriageBrief(BaseModel):
    company_id: str
    company_name: str
    website: str | None = None
    source: str = ""
    initial_fit_label: FitLabel = "maybe"
    summary: str = ""
    llm_score: int = Field(default=0, ge=0, le=100)
    deterministic_score: int = Field(default=0, ge=0, le=100)
    triage_score: int = Field(default=0, ge=0, le=100)
    confidence: ConfidenceLevel = "low"
    positive_signals: list[EvidenceBackedSignal] = Field(default_factory=list)
    negative_signals: list[EvidenceBackedSignal] = Field(default_factory=list)
    likely_pain_points: list[str] = Field(default_factory=list)
    disqualifiers: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    best_contact_persona: str | None = None
    personalized_hook: str | None = None
    discovery_question: str | None = None
    evidence_ids_used: list[str] = Field(default_factory=list)
    sources_checked: list[str] = Field(default_factory=list)
    evidence_score_mismatch: bool = False
