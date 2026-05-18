from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from customer_discovery.llm.validate import clamp_score

from customer_discovery.models.company import CompanyRecord
from customer_discovery.models.evidence import EvidenceBundle, cap_confidence, normalize_confidence
from customer_discovery.models.scoring import DeterministicFitScore, blend_triage_score
from customer_discovery.models.signals import EvidenceBackedSignal, ExtractedCompanySignals
from customer_discovery.models.triage import TriageBrief
from customer_discovery.research.agents.triage_postprocess import align_fit_label, merge_disqualifiers
from customer_discovery.research.prompts import build_triage_user_payload
from customer_discovery.llm.client import LLMClient


class TriageLLMOutput(BaseModel):
    initial_fit_label: str = "maybe"
    summary: str = ""
    llm_score: int = Field(ge=0, le=100, default=50)
    confidence: str = "low"
    positive_signals: list[dict] = Field(default_factory=list)
    negative_signals: list[dict] = Field(default_factory=list)
    likely_pain_points: list[str] = Field(default_factory=list)
    disqualifiers: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    best_contact_persona: str | None = None
    personalized_hook: str | None = None
    discovery_question: str | None = None
    evidence_ids_used: list[str] = Field(default_factory=list)

    @field_validator("llm_score", mode="before")
    @classmethod
    def _clamp_llm_score(cls, value: Any) -> int:
        return clamp_score(value, default=50)


TRIAGE_SYSTEM = """You are a research analyst triaging startup leads for B2B outreach.
Rules:
- Every claim must cite evidence_ids from the provided evidence blocks.
- Do not invent customers, tools, or integrations not in evidence.
- Say unclear when evidence is missing.
- Respect confidence_cap from coverage; do not exceed it.
- Apply product_disqualifiers strictly (especially hardware-heavy / minimal software ops).
- Do not label strong_candidate without on-call OR substantive API/developer docs in evidence.
- Robotics/software platforms serving enterprises are in-scope; robotic welding hardware is not.
- Output valid JSON matching the schema."""


def run_triage(
    company: CompanyRecord,
    bundle: EvidenceBundle,
    signals: ExtractedCompanySignals,
    det_score: DeterministicFitScore,
    *,
    llm: LLMClient,
    model: str,
    product: dict[str, Any],
    icp: dict[str, Any],
    blend_cfg: dict[str, float] | None = None,
) -> TriageBrief:
    user = build_triage_user_payload(
        company_name=company.name,
        website=str(company.website) if company.website else None,
        source=company.source,
        bundle=bundle,
        signals=signals,
        det_score=det_score,
        product=product,
        icp=icp,
    )
    out = llm.complete_json(
        model=model,
        system=TRIAGE_SYSTEM,
        user=user,
        schema=TriageLLMOutput,
    )
    blend = blend_cfg or {}
    triage_score = blend_triage_score(
        det_score.score,
        out.llm_score,
        det_weight=float(blend.get("deterministic_weight", 0.4)),
        llm_weight=float(blend.get("llm_weight", 0.6)),
    )
    conf = cap_confidence(normalize_confidence(out.confidence), bundle.coverage)
    mismatch = abs(det_score.score - out.llm_score) >= 25

    def map_signals(rows: list[dict]) -> list[EvidenceBackedSignal]:
        return [
            EvidenceBackedSignal(
                claim=r.get("claim", ""),
                evidence_ids=r.get("evidence_ids", []),
            )
            for r in rows
        ]

    disqualifiers = merge_disqualifiers(out.disqualifiers, signals, product)
    label = align_fit_label(out.initial_fit_label, triage_score, signals)

    return TriageBrief(
        company_id=company.id,
        company_name=company.name,
        website=str(company.website) if company.website else None,
        source=company.source,
        initial_fit_label=label,  # type: ignore[arg-type]
        summary=out.summary,
        llm_score=out.llm_score,
        deterministic_score=det_score.score,
        triage_score=triage_score,
        confidence=conf,
        positive_signals=map_signals(out.positive_signals),
        negative_signals=map_signals(out.negative_signals),
        likely_pain_points=out.likely_pain_points,
        disqualifiers=disqualifiers,
        missing_information=out.missing_information,
        best_contact_persona=out.best_contact_persona,
        personalized_hook=out.personalized_hook,
        discovery_question=out.discovery_question,
        evidence_ids_used=out.evidence_ids_used,
        sources_checked=[i.source_type for i in bundle.items if i.success],
        evidence_score_mismatch=mismatch,
    )
