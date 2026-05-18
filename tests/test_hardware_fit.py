from __future__ import annotations

from customer_discovery.models.company import CompanyRecord
from customer_discovery.models.evidence import EvidenceBundle, EvidenceCoverage, EvidenceItem, ResearchTrace
from customer_discovery.models.signals import ExtractedCompanySignals
from customer_discovery.research.agents.fit_scorer import score_fit
from customer_discovery.research.agents.signal_extractor import extract_signals
from customer_discovery.research.agents.triage_postprocess import align_fit_label
from customer_discovery.research.evidence_quality import qualifies_for_premium_llm
from customer_discovery.research.hardware_fit import is_hardware_heavy


def test_hexa_not_hardware_heavy():
    assert not is_hardware_heavy(
        industries=["B2B", "Artificial Intelligence"],
        homepage_text="The next generation of software for manufacturers and distributors.",
        description="AI workflow automation platform for enterprise supply chain.",
    )


def test_amr_hardware_heavy():
    assert is_hardware_heavy(
        industries=["Manufacturing", "Robotics"],
        homepage_text="Robotic welding systems for American manufacturing.",
        description="Machine intelligence for welding automation.",
    )


def test_robotics_software_not_hardware():
    assert not is_hardware_heavy(
        industries=["Robotics", "B2B", "Software"],
        homepage_text="Software platform for programming industrial robots in the cloud.",
        description="Developer APIs for robotics fleets.",
    )


def test_fit_scorer_penalizes_hardware():
    signals = ExtractedCompanySignals(
        company_id="amr",
        company_name="AMR",
        likely_b2b=True,
        has_api_docs=True,
        hardware_heavy=True,
        has_ops_evidence=False,
    )
    bundle = EvidenceBundle(
        company_id="amr",
        company_name="AMR",
        website="https://amr.com",
        coverage=EvidenceCoverage(
            homepage_found=True,
            docs_found=True,
            total_successful_sources=4,
        ),
        trace=ResearchTrace(),
    )
    company = CompanyRecord(id="amr", name="AMR", website="https://amr.com", source="yc")
    score = score_fit(signals, bundle, company)
    assert score.score <= 65
    assert "hardware_heavy" in score.negative_rules


def test_fit_scorer_rewards_ops_surface():
    signals = ExtractedCompanySignals(
        company_id="x",
        company_name="X",
        likely_b2b=True,
        has_substantive_docs=True,
        has_ops_evidence=True,
        mentions_on_call=True,
    )
    bundle = EvidenceBundle(
        company_id="x",
        company_name="X",
        website="https://x.com",
        coverage=EvidenceCoverage(homepage_found=True, careers_found=True),
        trace=ResearchTrace(),
    )
    company = CompanyRecord(id="x", name="X", website="https://x.com", source="yc")
    score = score_fit(signals, bundle, company)
    assert score.score >= 70
    assert "ops_surface_confirmed" in score.positive_rules


def test_align_fit_label_downgrades_hardware():
    signals = ExtractedCompanySignals(
        company_id="amr",
        company_name="AMR",
        hardware_heavy=True,
    )
    assert align_fit_label("strong_candidate", 90, signals) == "needs_review"


def test_premium_gate_blocks_hardware():
    signals = ExtractedCompanySignals(
        company_id="amr",
        company_name="AMR",
        hardware_heavy=True,
    )
    bundle = EvidenceBundle(
        company_id="amr",
        company_name="AMR",
        coverage=EvidenceCoverage(confidence_cap="high", total_successful_sources=5),
        trace=ResearchTrace(),
    )
    assert not qualifies_for_premium_llm(bundle, signals)


def test_extract_signals_hardware_from_description():
    bundle = EvidenceBundle(
        company_id="amr",
        company_name="AMR",
        items=[
            EvidenceItem(
                id="ev1",
                company_id="amr",
                source_type="homepage",
                text_snippet="Robotic welding systems for factories.",
                success=True,
            ),
        ],
        trace=ResearchTrace(),
    )
    sig = extract_signals(
        bundle,
        industries=["Manufacturing"],
        company_description="Welding robots",
    )
    assert sig.hardware_heavy
    assert not sig.has_ops_evidence
