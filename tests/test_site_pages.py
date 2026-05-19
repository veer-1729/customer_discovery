from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from customer_discovery.models.company import CompanyRecord
from customer_discovery.research.config import load_research_config
from customer_discovery.research.fetch import FetchResult, extract_text
from customer_discovery.research.tools import known_links, site_pages
from customer_discovery.research.tools.base import ToolContext
from customer_discovery.models.evidence import EvidenceItem, new_evidence_id

FIXTURE = (Path(__file__).parent / "fixtures" / "research" / "homepage_with_nav.html").read_text()


def test_site_pages_fetches_team_path(tmp_path: Path) -> None:
    company = CompanyRecord(
        id="acme-com",
        name="Acme",
        website="https://acme.com",
        source="yc",
    )
    cfg = load_research_config()
    ac = dict(cfg["agentic_collection"])
    ac["site_paths"] = ["/team"]
    ac["max_site_page_fetches"] = 2
    ac["min_site_page_chars"] = 20
    cfg = {**cfg, "agentic_collection": ac}
    cache = tmp_path / "raw"

    ctx = ToolContext(
        company=company,
        cfg=cfg,
        raw_cache_dir=cache,
        fetcher=None,  # type: ignore[arg-type]
    )
    ctx.discovered_links = {k: [] for k in known_links.LINK_PATTERNS}

    body = (
        "<html><body><h1>Our Team</h1>"
        "<p>Founders and engineers building the platform.</p></body></html>"
    )
    ok = FetchResult(
        url="https://acme.com/team",
        success=True,
        status_code=200,
        text=extract_text(body),
        html=body,
    )

    with patch(
        "customer_discovery.research.tools.site_pages.fetch_page",
        return_value=(ok, str(cache / "team.html")),
    ):
        site_pages.run_site_pages(ctx)

    assert any(i.url and "/team" in i.url for i in ctx.items if i.success)
