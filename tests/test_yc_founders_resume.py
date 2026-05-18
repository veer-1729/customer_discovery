from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from customer_discovery.models.company import CompanyRecord, TeamMember
from customer_discovery.pipeline.scrape import (
    founder_fetch_complete,
    has_team_seed,
    prepare_source_options,
    slugs_with_team_seed,
)
from customer_discovery.sources.yc import _parse_founders_from_rsc_html, scrape_founders_for_slug
from customer_discovery.sources.yc import YCSource
from customer_discovery.sources.yc_filters import YCFilterConfig


def test_has_team_seed():
    assert not has_team_seed(CompanyRecord(id="a", name="A", source="yc"))
    assert has_team_seed(
        CompanyRecord(
            id="a",
            name="A",
            source="yc",
            team=[TeamMember(name="Jane")],
        )
    )


def test_founder_fetch_complete_flag():
    rec = CompanyRecord(
        id="x",
        name="X",
        source="yc",
        raw={"slug": "x", "founders_page_fetched": True},
    )
    assert founder_fetch_complete(rec)
    assert "x" in slugs_with_team_seed([rec])


def test_parse_founders_from_rsc_fixture():
    html = (
        Path(__file__).parent / "fixtures" / "yc" / "company_page_snippet.html"
    ).read_text()
    founders = _parse_founders_from_rsc_html(html)
    assert len(founders) == 1
    assert founders[0].name == "Jane Founder"
    assert founders[0].role == "CEO"


def test_slugs_with_team_seed():
    records = [
        CompanyRecord(
            id="a",
            name="A",
            source="yc",
            raw={"slug": "a-corp"},
            team=[TeamMember(name="Jane")],
        ),
        CompanyRecord(
            id="b",
            name="B",
            source="yc",
            raw={"slug": "b-corp"},
        ),
    ]
    assert slugs_with_team_seed(records) == {"a-corp"}


def test_prepare_source_options_injects_skip_slugs():
    existing = [
        CompanyRecord(
            id="x",
            name="X",
            source="yc",
            raw={"slug": "x"},
            team=[TeamMember(name="Founder")],
        )
    ]
    opts = prepare_source_options({"fetch_founders": True}, existing)
    assert opts["skip_founder_slugs"] == {"x"}


@pytest.mark.asyncio
async def test_yc_skips_founder_fetch_for_slug():
    hit = {
        "name": "TestCo",
        "slug": "testco",
        "website": "https://test.co",
        "batch": "W24",
    }

    async def run():
        source = YCSource()
        options = {
            "filter_config": YCFilterConfig(),
            "fetch_founders": True,
            "skip_founder_slugs": {"testco"},
            "rate_limit_rps": 100,
        }
        with patch("customer_discovery.sources.yc.algolia_query") as mock_alg:
            mock_alg.return_value = {"hits": [hit], "nbPages": 1}
            with patch(
                "customer_discovery.sources.yc.scrape_founders_for_slug"
            ) as mock_founders:
                records = []
                async for rec in source.scrape(limit=1, **options):
                    records.append(rec)
                mock_founders.assert_not_called()
                assert len(records) == 1
                assert records[0].team == []

    await run()
