from __future__ import annotations

from customer_discovery.models.company import CompanyRecord
from customer_discovery.models.evidence import EvidenceBundle, EvidenceCoverage, ResearchTrace
from customer_discovery.models.scoring import DeterministicFitScore
from customer_discovery.models.signals import ExtractedCompanySignals
from customer_discovery.llm.client import MockLLMClient
from customer_discovery.research.agents.triage import run_triage


def test_triage_with_mock_llm():
    bundle = EvidenceBundle(
        company_id="c",
        company_name="C",
        website="https://c.com",
        coverage=EvidenceCoverage(confidence_cap="medium", homepage_found=True),
        trace=ResearchTrace(),
    )
    signals = ExtractedCompanySignals(company_id="c", company_name="C", likely_b2b=True)
    det = DeterministicFitScore(company_id="c", score=65)
    company = CompanyRecord(id="c", name="C", website="https://c.com", source="yc")
    llm = MockLLMClient(
        {
            "TriageLLMOutput": {
                "initial_fit_label": "strong_candidate",
                "summary": "B2B API company",
                "llm_score": 72,
                "confidence": "medium",
                "positive_signals": [{"claim": "API docs", "evidence_ids": []}],
                "negative_signals": [],
                "evidence_ids_used": [],
            }
        }
    )
    brief = run_triage(
        company,
        bundle,
        signals,
        det,
        llm=llm,
        model="gpt-4o-mini",
        product={"name": "Test"},
        icp={},
    )
    assert brief.initial_fit_label == "strong_candidate"
    assert brief.triage_score > 0
