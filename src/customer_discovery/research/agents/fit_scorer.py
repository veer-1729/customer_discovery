from __future__ import annotations

from customer_discovery.models.company import CompanyRecord
from customer_discovery.models.evidence import EvidenceBundle
from customer_discovery.models.scoring import DeterministicFitScore
from customer_discovery.models.signals import ExtractedCompanySignals


def score_fit(
    signals: ExtractedCompanySignals,
    bundle: EvidenceBundle,
    company: CompanyRecord,
) -> DeterministicFitScore:
    score = 50
    positive: list[str] = []
    negative: list[str] = []

    if signals.likely_b2b:
        score += 20
        positive.append("b2b_or_devtools_signal")
    if signals.has_substantive_docs:
        score += 15
        positive.append("substantive_api_docs")
    elif signals.has_api_docs:
        score += 5
        positive.append("thin_or_unverified_docs_path")
    if signals.has_integrations or signals.has_webhooks:
        score += 10
        positive.append("integrations_or_webhooks")
    if signals.hiring_backend or signals.hiring_platform or signals.hiring_infra_sre:
        score += 20
        positive.append("hiring_backend_platform_infra")
    if signals.mentions_on_call:
        score += 20
        positive.append("on_call_reliability_language")
    if bundle.coverage.status_found or bundle.coverage.github_found or bundle.coverage.blog_or_changelog_found:
        score += 10
        positive.append("status_changelog_github_footprint")
    if signals.likely_production_critical:
        score += 10
        positive.append("likely_production_critical")
    if signals.has_ops_evidence:
        positive.append("ops_surface_confirmed")
    if company.batch or company.source in ("yc", "cmu"):
        score += 10
        positive.append("ideal_stage_metadata")

    if signals.hardware_heavy:
        score -= 35
        negative.append("hardware_heavy")
    if "pre_launch_signals" in signals.negative_signals_detected:
        score -= 20
        negative.append("pre_launch")
    if signals.likely_consumer:
        score -= 15
        negative.append("consumer_only")
    if "mature_sre_org_signals" in signals.negative_signals_detected:
        score -= 10
        negative.append("mature_sre_org")
    if not bundle.website or bundle.coverage.total_successful_sources <= 1:
        score -= 10
        negative.append("weak_public_evidence")
    if not signals.has_ops_evidence:
        score -= 15
        negative.append("no_on_call_or_substantive_docs")

    score = max(0, min(100, score))
    return DeterministicFitScore(
        company_id=signals.company_id,
        score=score,
        positive_rules=positive,
        negative_rules=negative,
    )
