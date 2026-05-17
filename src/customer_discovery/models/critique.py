from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from customer_discovery.models.evidence import ConfidenceLevel
from customer_discovery.models.signals import EvidenceBackedSignal
from customer_discovery.models.triage import FitLabel

FinalStage = Literal["triage", "reviewed", "premium"]


class AdvisorCritique(BaseModel):
    company_id: str
    approved: bool = False
    unsupported_claims: list[str] = Field(default_factory=list)
    recommended_score_adjustment: int = 0
    should_advance_to_premium: bool = False
    revision_instructions: str = ""
    needs_manual_review: bool = False
    notes: str = ""


class ReviewedBrief(BaseModel):
    company_id: str
    company_name: str
    website: str | None = None
    source: str = ""
    fit_label: FitLabel = "maybe"
    summary: str = ""
    reviewed_score: int = Field(default=0, ge=0, le=100)
    deterministic_score: int = Field(default=0, ge=0, le=100)
    confidence: ConfidenceLevel = "low"
    positive_signals: list[EvidenceBackedSignal] = Field(default_factory=list)
    negative_signals: list[EvidenceBackedSignal] = Field(default_factory=list)
    likely_pain_points: list[str] = Field(default_factory=list)
    disqualifiers: list[str] = Field(default_factory=list)
    best_contact_persona: str | None = None
    personalized_hook: str | None = None
    discovery_question: str | None = None
    evidence_ids_used: list[str] = Field(default_factory=list)
    sources_checked: list[str] = Field(default_factory=list)
    critique_notes: str = ""
    needs_manual_review: bool = False
    final_stage: FinalStage = "reviewed"
