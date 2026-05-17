from __future__ import annotations

from pydantic import BaseModel, Field

from customer_discovery.models.critique import FinalStage
from customer_discovery.models.evidence import ConfidenceLevel
from customer_discovery.models.signals import EvidenceBackedSignal
from customer_discovery.models.triage import FitLabel


class UrlNote(BaseModel):
    url: str
    why_important: str


class PremiumBrief(BaseModel):
    company_id: str
    company_name: str
    website: str | None = None
    source: str = ""
    fit_label: FitLabel = "strong_candidate"
    summary: str = ""
    premium_score: int = Field(default=0, ge=0, le=100)
    confidence: ConfidenceLevel = "medium"
    icp_fit_summary: str = ""
    why_product_might_apply: str = ""
    positive_signals: list[EvidenceBackedSignal] = Field(default_factory=list)
    negative_signals: list[EvidenceBackedSignal] = Field(default_factory=list)
    likely_pain_points: list[str] = Field(default_factory=list)
    disqualifiers: list[str] = Field(default_factory=list)
    best_contact_persona: str | None = None
    personalized_hook: str | None = None
    discovery_question: str | None = None
    evidence_ids_used: list[str] = Field(default_factory=list)
    url_notes: list[UrlNote] = Field(default_factory=list)
    review_warnings: list[str] = Field(default_factory=list)
    final_stage: FinalStage = "premium"
