from __future__ import annotations

from customer_discovery.models.evidence import (
    EvidenceBundle,
    EvidenceCoverage,
    EvidenceItem,
    ResearchTrace,
    new_evidence_id,
)
from customer_discovery.research.pipeline.url_catalog import build_important_urls


def _item(st: str, url: str, eid: str | None = None, success: bool = True) -> EvidenceItem:
    return EvidenceItem(
        id=eid or new_evidence_id(),
        company_id="acme-com",
        source_type=st,  # type: ignore[arg-type]
        url=url,
        text_snippet="x",
        success=success,
    )


def test_build_important_urls_includes_all_evidence_urls():
    bundle = EvidenceBundle(
        company_id="acme-com",
        company_name="Acme",
        items=[
            _item("homepage", "https://acme.com", "ev1"),
            _item("careers", "https://acme.com/careers", "ev2"),
            _item("docs", "https://docs.acme.com", "ev3"),
            _item("search_result", "https://jobs.lever.co/acme", "ev4"),
            _item("fallback_page", "https://acme.com/jobs", "ev5"),
        ],
        coverage=EvidenceCoverage(),
        trace=ResearchTrace(),
    )
    urls = build_important_urls(bundle, ["ev1"])
    url_set = {u.url for u in urls}
    assert url_set == {
        "https://acme.com",
        "https://acme.com/careers",
        "https://docs.acme.com",
        "https://jobs.lever.co/acme",
        "https://acme.com/jobs",
    }
    assert len(urls) == 5


def test_build_important_urls_includes_failed_fetch_urls():
    bundle = EvidenceBundle(
        company_id="acme-com",
        company_name="Acme",
        items=[
            _item("docs", "https://acme.com/docs", success=False),
        ],
        coverage=EvidenceCoverage(),
        trace=ResearchTrace(urls_attempted=["https://acme.com/missing"]),
    )
    urls = build_important_urls(bundle, [])
    assert len(urls) == 2
    assert any(u.url == "https://acme.com/docs" for u in urls)
    assert any(u.url == "https://acme.com/missing" for u in urls)


def test_dedupes_same_url_different_items():
    bundle = EvidenceBundle(
        company_id="acme-com",
        company_name="Acme",
        items=[
            _item("careers", "https://acme.com/jobs", "ev1"),
            _item("fallback_page", "https://acme.com/jobs", "ev2"),
        ],
        coverage=EvidenceCoverage(),
        trace=ResearchTrace(),
    )
    urls = build_important_urls(bundle, ["ev2"])
    assert len(urls) == 1
    assert urls[0].used_in_reasoning is True
