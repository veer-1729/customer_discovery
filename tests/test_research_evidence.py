from __future__ import annotations

from customer_discovery.models.company import CompanyRecord
from customer_discovery.models.evidence import EvidenceItem, compute_coverage, new_evidence_id
from customer_discovery.research.agents.signal_extractor import extract_signals
from customer_discovery.models.evidence import EvidenceBundle, EvidenceCoverage, ResearchTrace
from customer_discovery.research.keywords import has_careers_signal, has_docs_signal


def _item(source_type: str, text: str, **kwargs) -> EvidenceItem:
    return EvidenceItem(
        id=new_evidence_id(),
        company_id="acme-com",
        source_type=source_type,  # type: ignore[arg-type]
        url=kwargs.get("url", "https://example.com"),
        text_snippet=text,
        success=True,
    )


def test_compute_coverage_high_with_homepage_careers_docs():
    items = [
        _item("homepage", "B2B SaaS platform"),
        _item("careers", "Hiring backend engineer on-call rotation"),
        _item("docs", "REST API webhooks integrations"),
    ]
    cov = compute_coverage(items)
    assert cov.homepage_found
    assert cov.careers_found
    assert cov.docs_found
    assert cov.confidence_cap == "high"


def test_extract_signals_on_call_and_api():
    bundle = EvidenceBundle(
        company_id="acme-com",
        company_name="Acme",
        items=[
            _item("careers", "Platform engineer on-call incident response"),
            _item("docs", "API reference webhooks OAuth"),
        ],
        coverage=EvidenceCoverage(),
        trace=ResearchTrace(),
    )
    sig = extract_signals(bundle)
    assert sig.hiring_platform
    assert sig.mentions_on_call
    assert sig.has_api_docs


def test_keyword_helpers():
    assert has_careers_signal("We are hiring a backend engineer")
    assert has_docs_signal("REST API documentation webhooks")
