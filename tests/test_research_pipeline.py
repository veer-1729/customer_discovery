from __future__ import annotations

from customer_discovery.models.evidence import EvidenceBundle, EvidenceCoverage, ResearchTrace
from customer_discovery.models.evidence import EvidenceItem, new_evidence_id
from customer_discovery.models.final import FinalBrief
from customer_discovery.models.triage import TriageBrief
from customer_discovery.models.critique import ReviewedBrief
from customer_discovery.research.pipeline.final_selector import select_final_brief
from customer_discovery.research.pipeline.url_catalog import build_important_urls, best_url_by_type
from customer_discovery.research.pipeline.cost_estimate import estimate_run_cost


def _item(st: str, url: str, eid: str) -> EvidenceItem:
    return EvidenceItem(
        id=eid,
        company_id="c",
        source_type=st,  # type: ignore[arg-type]
        url=url,
        text_snippet="text",
        success=True,
    )


def test_final_selector_prefers_premium():
    bundle = EvidenceBundle(
        company_id="c",
        company_name="C",
        items=[_item("homepage", "https://c.com", "ev1")],
        coverage=EvidenceCoverage(),
        trace=ResearchTrace(),
    )
    triage = TriageBrief(company_id="c", company_name="C", triage_score=50)
    from customer_discovery.models.premium import PremiumBrief

    premium = PremiumBrief(company_id="c", company_name="C", premium_score=90)
    fb = select_final_brief("c", bundle, triage, None, premium)
    assert fb.final_stage == "premium"
    assert fb.final_score == 90


def test_important_urls_used_in_reasoning():
    bundle = EvidenceBundle(
        company_id="c",
        company_name="C",
        items=[
            _item("homepage", "https://c.com", "ev1"),
            _item("careers", "https://c.com/careers", "ev2"),
            _item("search_result", "https://lever.co/c", "ev3"),
        ],
        coverage=EvidenceCoverage(),
        trace=ResearchTrace(),
    )
    urls = build_important_urls(bundle, ["ev1"])
    assert len(urls) == 3
    used = [u for u in urls if u.used_in_reasoning]
    assert any(u.url == "https://c.com" for u in used)
    assert best_url_by_type(bundle, "careers") == "https://c.com/careers"


def test_cost_estimate():
    est = estimate_run_cost(100, {"cost_estimates": {}, "models": {}, "stages": {"premium": {"top_n": 50}}})
    assert est["companies"] == 100
    assert "total" in est["estimated_usd"]
