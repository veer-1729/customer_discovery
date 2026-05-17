from __future__ import annotations

from customer_discovery.models.company import CompanyRecord
from customer_discovery.models.evidence import EvidenceBundle, EvidenceCoverage, ResearchTrace
from customer_discovery.models.signals import ExtractedCompanySignals
from customer_discovery.research.agents.fit_scorer import score_fit
from customer_discovery.models.scoring import blend_triage_score


def test_fit_scorer_rewards_b2b_and_on_call():
    signals = ExtractedCompanySignals(
        company_id="x",
        company_name="X",
        likely_b2b=True,
        has_api_docs=True,
        hiring_backend=True,
        mentions_on_call=True,
    )
    bundle = EvidenceBundle(
        company_id="x",
        company_name="X",
        website="https://x.com",
        coverage=EvidenceCoverage(homepage_found=True, careers_found=True, status_found=True),
        trace=ResearchTrace(),
    )
    company = CompanyRecord(id="x", name="X", website="https://x.com", source="yc", batch="W24")
    score = score_fit(signals, bundle, company)
    assert score.score >= 70
    assert "b2b_or_devtools_signal" in score.positive_rules


def test_blend_triage_score():
    assert blend_triage_score(80, 60) == 68
