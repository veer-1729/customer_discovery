from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from customer_discovery.models.critique import AdvisorCritique, ReviewedBrief
from customer_discovery.models.evidence import EvidenceCoverage, cap_confidence
from customer_discovery.models.signals import EvidenceBackedSignal
from customer_discovery.models.triage import TriageBrief
from customer_discovery.llm.client import LLMClient


class CritiqueLLMOutput(BaseModel):
    approved: bool = False
    unsupported_claims: list[str] = Field(default_factory=list)
    recommended_score_adjustment: int = 0
    should_advance_to_premium: bool = False
    revision_instructions: str = ""
    needs_manual_review: bool = False
    notes: str = ""


class RevisionLLMOutput(BaseModel):
    fit_label: str = "maybe"
    summary: str = ""
    reviewed_score: int = Field(ge=0, le=100, default=50)
    confidence: str = "medium"
    positive_signals: list[dict] = Field(default_factory=list)
    negative_signals: list[dict] = Field(default_factory=list)
    likely_pain_points: list[str] = Field(default_factory=list)
    disqualifiers: list[str] = Field(default_factory=list)
    best_contact_persona: str | None = None
    personalized_hook: str | None = None
    discovery_question: str | None = None
    evidence_ids_used: list[str] = Field(default_factory=list)


CRITIC_SYSTEM = """You are a skeptical advisor reviewing a triage brief.
Flag unsupported claims, hallucinations, and overconfident scores.
Recommend score adjustments. Output JSON only."""


REVISION_SYSTEM = """Revise the triage brief once based on critique instructions.
Remove unsupported claims. Cite only valid evidence_ids. Output JSON only."""


def should_run_critic(triage: TriageBrief, cfg: dict[str, Any]) -> bool:
    stage = cfg.get("stages", {}).get("critic", {})
    if triage.initial_fit_label == "skip":
        return False
    min_score = stage.get("min_score", 60)
    labels = stage.get("labels", ["strong_candidate", "needs_review"])
    if triage.triage_score >= min_score:
        return True
    if triage.initial_fit_label in labels:
        return True
    if triage.confidence in ("medium", "high"):
        return True
    if triage.evidence_score_mismatch:
        return True
    return False


def run_critic(
    triage: TriageBrief,
    *,
    llm: LLMClient,
    model: str,
) -> AdvisorCritique:
    user = json.dumps(triage.model_dump(), indent=2)
    out = llm.complete_json(
        model=model,
        system=CRITIC_SYSTEM,
        user=user,
        schema=CritiqueLLMOutput,
    )
    return AdvisorCritique(
        company_id=triage.company_id,
        approved=out.approved,
        unsupported_claims=out.unsupported_claims,
        recommended_score_adjustment=out.recommended_score_adjustment,
        should_advance_to_premium=out.should_advance_to_premium,
        revision_instructions=out.revision_instructions,
        needs_manual_review=out.needs_manual_review,
        notes=out.notes,
    )


def run_revision(
    triage: TriageBrief,
    critique: AdvisorCritique,
    *,
    llm: LLMClient,
    model: str,
    coverage: EvidenceCoverage,
) -> ReviewedBrief:
    user = json.dumps(
        {"triage": triage.model_dump(), "critique": critique.model_dump()},
        indent=2,
    )
    out = llm.complete_json(
        model=model,
        system=REVISION_SYSTEM,
        user=user,
        schema=RevisionLLMOutput,
    )
    score = max(0, min(100, triage.triage_score + critique.recommended_score_adjustment))
    score = max(score, out.reviewed_score)
    conf = cap_confidence(out.confidence, coverage)  # type: ignore[arg-type]

    def map_signals(rows: list[dict]) -> list[EvidenceBackedSignal]:
        return [
            EvidenceBackedSignal(
                claim=r.get("claim", ""),
                evidence_ids=r.get("evidence_ids", []),
            )
            for r in rows
        ]

    return ReviewedBrief(
        company_id=triage.company_id,
        company_name=triage.company_name,
        website=triage.website,
        source=triage.source,
        fit_label=out.fit_label if out.fit_label in ("skip", "maybe", "strong_candidate", "needs_review") else triage.initial_fit_label,  # type: ignore
        summary=out.summary or triage.summary,
        reviewed_score=score,
        deterministic_score=triage.deterministic_score,
        confidence=conf,
        positive_signals=map_signals(out.positive_signals) or triage.positive_signals,
        negative_signals=map_signals(out.negative_signals) or triage.negative_signals,
        likely_pain_points=out.likely_pain_points or triage.likely_pain_points,
        disqualifiers=out.disqualifiers or triage.disqualifiers,
        best_contact_persona=out.best_contact_persona or triage.best_contact_persona,
        personalized_hook=out.personalized_hook or triage.personalized_hook,
        discovery_question=out.discovery_question or triage.discovery_question,
        evidence_ids_used=out.evidence_ids_used or triage.evidence_ids_used,
        sources_checked=triage.sources_checked,
        critique_notes=critique.notes,
        needs_manual_review=critique.needs_manual_review,
    )
