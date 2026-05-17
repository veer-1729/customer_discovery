from customer_discovery.models.company import CompanyRecord
from customer_discovery.pipeline.dedup import DedupIndex


def test_dedup_by_domain_merges():
    a = CompanyRecord(
        id="x",
        name="Acme",
        website="https://www.acme.com",
        source="yc",
        industry=["B2B"],
    )
    b = CompanyRecord(
        id="y",
        name="Acme Inc",
        website="https://acme.com/about",
        source="cmu",
        description="From CMU list",
        industry=["SaaS"],
    )
    index = DedupIndex()
    index.add(a)
    index.add(b)
    assert len(index) == 1
    merged = index.values()[0]
    assert "B2B" in merged.industry and "SaaS" in merged.industry
    assert merged.description == "From CMU list"
