"""Prove known_links + deterministic path fetching on fixture HTML."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from customer_discovery.models.company import CompanyRecord
from customer_discovery.research.agents.evidence_collector import collect_evidence
from customer_discovery.research.agents.signal_extractor import extract_signals
from customer_discovery.research.config import load_research_config
from customer_discovery.research.fetch import FetchResult, PageFetcher, extract_text
from customer_discovery.research.tools import known_links
from customer_discovery.research.tools.base import ToolContext
from customer_discovery.research.tools.search_fallback import SearchFallbackTool

FIXTURE_HTML = (
    Path(__file__).parent / "fixtures" / "research" / "homepage_with_nav.html"
).read_text()


@pytest.fixture
def acme_company() -> CompanyRecord:
    return CompanyRecord(
        id="acme-com",
        name="Acme",
        website="https://acme.com",
        description="B2B SaaS",
        source="yc",
        links={"github": "https://github.com/acme"},
    )


def test_known_links_buckets_fixture_nav(acme_company: CompanyRecord, tmp_path: Path) -> None:
    cfg = load_research_config()
    cache = tmp_path / "raw"
    cache.mkdir()
    homepage_path = cache / acme_company.id / "home.html"
    homepage_path.parent.mkdir(parents=True)
    homepage_path.write_text(FIXTURE_HTML)

    ctx = ToolContext(
        company=acme_company,
        cfg=cfg,
        raw_cache_dir=cache,
        fetcher=None,  # type: ignore[arg-type]
    )
    from customer_discovery.models.evidence import EvidenceItem, new_evidence_id

    ctx.items.append(
        EvidenceItem(
            id=new_evidence_id(),
            company_id=acme_company.id,
            source_type="homepage",
            url="https://acme.com",
            success=True,
            raw_cache_path=str(homepage_path),
        )
    )
    known_links.run_known_links_extract(ctx)
    d = ctx.discovered_links
    assert "https://acme.com/careers" in d["careers"]
    assert any("docs.acme.com" in u for u in d["docs"])
    assert any("status.acme.com" in u for u in d["status"])
    assert any("github.com/acme" in u for u in d["github"])
    assert "https://acme.com/blog" in d["blog"]


def test_collect_evidence_finds_careers_from_nav(acme_company: CompanyRecord, tmp_path: Path) -> None:
    cfg = load_research_config()
    SearchFallbackTool.configure(cfg, enabled=False)

    def fake_page_fetch(self, url: str) -> FetchResult:
        from urllib.parse import urlparse

        host = urlparse(url).netloc
        path = urlparse(url).path or "/"
        if host == "acme.com" and path.startswith("/careers"):
            body = (
                "<html><body><h1>Careers</h1>"
                "<p>Hiring backend engineer on-call rotation.</p></body></html>"
            )
        elif host == "acme.com" and path in ("/", ""):
            body = FIXTURE_HTML
        else:
            body = "<html><body><p>REST API documentation webhooks</p></body></html>"
        return FetchResult(
            url=url,
            success=True,
            status_code=200,
            title="T",
            text=extract_text(body),
            html=body,
        )

    with patch.object(PageFetcher, "fetch", fake_page_fetch):
        bundle = collect_evidence(
            acme_company,
            cfg,
            raw_cache_dir=tmp_path / "cache",
            search_enabled=False,
            force_refetch=True,
        )

    types = {i.source_type for i in bundle.items if i.success}
    assert "homepage" in types
    assert "careers" in types
    sig = extract_signals(bundle)
    assert sig.hiring_backend or sig.mentions_on_call
    assert bundle.coverage.careers_found
