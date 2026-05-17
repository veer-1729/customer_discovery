from __future__ import annotations

from customer_discovery.models.critique import ReviewedBrief
from customer_discovery.models.evidence import EvidenceBundle
from customer_discovery.models.final import FinalBrief
from customer_discovery.models.premium import PremiumBrief
from customer_discovery.models.triage import TriageBrief
from customer_discovery.research.pipeline.url_catalog import build_important_urls


def select_final_brief(
    company_id: str,
    bundle: EvidenceBundle,
    triage: TriageBrief | None,
    reviewed: ReviewedBrief | None,
    premium: PremiumBrief | None,
) -> FinalBrief:
    if premium:
        return _from_premium(premium, bundle)
    if reviewed:
        return _from_reviewed(reviewed, bundle)
    if triage:
        return _from_triage(triage, bundle)
    raise ValueError(f"No brief available for {company_id}")


def _from_triage(triage: TriageBrief, bundle: EvidenceBundle) -> FinalBrief:
    return FinalBrief(
        company_id=triage.company_id,
        company_name=triage.company_name,
        website=triage.website,
        source=triage.source,
        final_score=triage.triage_score,
        confidence=triage.confidence,
        final_stage="triage",
        fit_label=triage.initial_fit_label,
        summary=triage.summary,
        positive_signals=triage.positive_signals,
        negative_signals=triage.negative_signals,
        likely_pain_points=triage.likely_pain_points,
        disqualifiers=triage.disqualifiers,
        best_contact_persona=triage.best_contact_persona,
        personalized_hook=triage.personalized_hook,
        suggested_discovery_question=triage.discovery_question,
        evidence_ids_used=triage.evidence_ids_used,
        important_urls=build_important_urls(bundle, triage.evidence_ids_used),
        manual_review_required=triage.initial_fit_label == "needs_review",
    )


def _from_reviewed(reviewed: ReviewedBrief, bundle: EvidenceBundle) -> FinalBrief:
    return FinalBrief(
        company_id=reviewed.company_id,
        company_name=reviewed.company_name,
        website=reviewed.website,
        source=reviewed.source,
        final_score=reviewed.reviewed_score,
        confidence=reviewed.confidence,
        final_stage="reviewed",
        fit_label=reviewed.fit_label,
        summary=reviewed.summary,
        positive_signals=reviewed.positive_signals,
        negative_signals=reviewed.negative_signals,
        likely_pain_points=reviewed.likely_pain_points,
        disqualifiers=reviewed.disqualifiers,
        best_contact_persona=reviewed.best_contact_persona,
        personalized_hook=reviewed.personalized_hook,
        suggested_discovery_question=reviewed.discovery_question,
        evidence_ids_used=reviewed.evidence_ids_used,
        important_urls=build_important_urls(bundle, reviewed.evidence_ids_used),
        manual_review_required=reviewed.needs_manual_review,
    )


def _from_premium(premium: PremiumBrief, bundle: EvidenceBundle) -> FinalBrief:
    return FinalBrief(
        company_id=premium.company_id,
        company_name=premium.company_name,
        website=premium.website,
        source=premium.source,
        final_score=premium.premium_score,
        confidence=premium.confidence,
        final_stage="premium",
        fit_label=premium.fit_label,
        summary=premium.summary,
        positive_signals=premium.positive_signals,
        negative_signals=premium.negative_signals,
        likely_pain_points=premium.likely_pain_points,
        disqualifiers=premium.disqualifiers,
        best_contact_persona=premium.best_contact_persona,
        personalized_hook=premium.personalized_hook,
        suggested_discovery_question=premium.discovery_question,
        evidence_ids_used=premium.evidence_ids_used,
        important_urls=build_important_urls(
            bundle, premium.evidence_ids_used, premium=premium
        ),
        manual_review_required=bool(premium.review_warnings),
    )
