from __future__ import annotations

from pydantic import BaseModel, Field

from customer_discovery.models.critique import FinalStage
from customer_discovery.models.evidence import ConfidenceLevel
from customer_discovery.models.signals import EvidenceBackedSignal
from customer_discovery.models.triage import FitLabel


class ImportantURL(BaseModel):
    url: str
    source_type: str
    why_important: str
    used_in_reasoning: bool = False


class FinalBrief(BaseModel):
    company_id: str
    company_name: str
    website: str | None = None
    source: str = ""
    final_score: int = Field(default=0, ge=0, le=100)
    confidence: ConfidenceLevel = "low"
    final_stage: FinalStage = "triage"
    fit_label: FitLabel = "maybe"
    summary: str = ""
    positive_signals: list[EvidenceBackedSignal] = Field(default_factory=list)
    negative_signals: list[EvidenceBackedSignal] = Field(default_factory=list)
    likely_pain_points: list[str] = Field(default_factory=list)
    disqualifiers: list[str] = Field(default_factory=list)
    best_contact_persona: str | None = None
    personalized_hook: str | None = None
    suggested_discovery_question: str | None = None
    evidence_ids_used: list[str] = Field(default_factory=list)
    important_urls: list[ImportantURL] = Field(default_factory=list)
    manual_review_required: bool = False
    rank: int | None = None
