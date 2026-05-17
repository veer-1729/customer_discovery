from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from customer_discovery.models.company import CompanyRecord
from customer_discovery.models.critique import ReviewedBrief
from customer_discovery.models.evidence import EvidenceBundle, cap_confidence
from customer_discovery.models.premium import PremiumBrief, UrlNote
from customer_discovery.models.signals import EvidenceBackedSignal
from customer_discovery.models.triage import TriageBrief
from customer_discovery.research.prompts import build_triage_user_payload, evidence_digest
from customer_discovery.models.scoring import DeterministicFitScore
from customer_discovery.models.signals import ExtractedCompanySignals
from customer_discovery.llm.client import LLMClient


class PremiumLLMOutput(BaseModel):
    fit_label: str = "strong_candidate"
    summary: str = ""
    premium_score: int = Field(ge=0, le=100, default=75)
    confidence: str = "medium"
    icp_fit_summary: str = ""
    why_product_might_apply: str = ""
    positive_signals: list[dict] = Field(default_factory=list)
    negative_signals: list[dict] = Field(default_factory=list)
    likely_pain_points: list[str] = Field(default_factory=list)
    disqualifiers: list[str] = Field(default_factory=list)
    best_contact_persona: str | None = None
    personalized_hook: str | None = None
    discovery_question: str | None = None
    evidence_ids_used: list[str] = Field(default_factory=list)
    url_notes: list[dict] = Field(default_factory=list)
    review_warnings: list[str] = Field(default_factory=list)


PREMIUM_SYSTEM = """You are a senior research analyst preparing outreach-ready briefs.
Be specific, evidence-backed, and technical. Cite evidence_ids. Output JSON only."""


def run_premium(
    company: CompanyRecord,
    bundle: EvidenceBundle,
    signals: ExtractedCompanySignals,
    det_score: DeterministicFitScore,
    brief: TriageBrief | ReviewedBrief,
    *,
    llm: LLMClient,
    model: str,
    product: dict[str, Any],
    icp: dict[str, Any],
) -> PremiumBrief:
    base = build_triage_user_payload(
        company_name=company.name,
        website=str(company.website) if company.website else None,
        source=company.source,
        bundle=bundle,
        signals=signals,
        det_score=det_score,
        product=product,
        icp=icp,
    )
    user = json.dumps(
        {
            "prior_brief": brief.model_dump(),
            "evidence": evidence_digest(bundle, max_items=15),
            "context": json.loads(base),
        },
        indent=2,
    )
    out = llm.complete_json(
        model=model,
        system=PREMIUM_SYSTEM,
        user=user,
        schema=PremiumLLMOutput,
    )

    def map_signals(rows: list[dict]) -> list[EvidenceBackedSignal]:
        return [
            EvidenceBackedSignal(
                claim=r.get("claim", ""),
                evidence_ids=r.get("evidence_ids", []),
            )
            for r in rows
        ]

    url_notes = [
        UrlNote(url=n.get("url", ""), why_important=n.get("why_important", ""))
        for n in out.url_notes
        if n.get("url")
    ]
    conf = cap_confidence(out.confidence, bundle.coverage)  # type: ignore[arg-type]
    label = out.fit_label if out.fit_label in ("skip", "maybe", "strong_candidate", "needs_review") else "strong_candidate"

    return PremiumBrief(
        company_id=company.id,
        company_name=company.name,
        website=str(company.website) if company.website else None,
        source=company.source,
        fit_label=label,  # type: ignore[arg-type]
        summary=out.summary,
        premium_score=out.premium_score,
        confidence=conf,
        icp_fit_summary=out.icp_fit_summary,
        why_product_might_apply=out.why_product_might_apply,
        positive_signals=map_signals(out.positive_signals),
        negative_signals=map_signals(out.negative_signals),
        likely_pain_points=out.likely_pain_points,
        disqualifiers=out.disqualifiers,
        best_contact_persona=out.best_contact_persona,
        personalized_hook=out.personalized_hook,
        discovery_question=out.discovery_question,
        evidence_ids_used=out.evidence_ids_used,
        url_notes=url_notes,
        review_warnings=out.review_warnings,
    )
