from __future__ import annotations

from customer_discovery.research.search.base import SearchResult
from customer_discovery.research.search_relevance import (
    filter_search_results,
    is_relevant_search_url,
)


def test_rejects_homonym_domain():
    assert not is_relevant_search_url(
        "https://www.aquasec.com/about-us/careers/",
        company_domain="aquashieldai.com",
    )
    assert not is_relevant_search_url(
        "https://www.panaceasmartsolutions.com/career/",
        company_domain="withpanacea.com",
    )
    assert not is_relevant_search_url(
        "https://deepiq.com/career/",
        company_domain="deepinteractions.ai",
    )
    assert not is_relevant_search_url(
        "https://jobs.bvp.com/jobs/guild-education",
        company_domain="guildai.co",
    )


def test_accepts_company_domain_and_subdomain():
    assert is_relevant_search_url(
        "https://www.watolabs.com/about",
        company_domain="watolabs.com",
    )
    assert is_relevant_search_url(
        "https://docs.watolabs.com/api",
        company_domain="watolabs.com",
    )


def test_accepts_ats_and_blocks_aggregators():
    assert is_relevant_search_url(
        "https://jobs.ashbyhq.com/acme",
        company_domain="acme.com",
    )
    assert not is_relevant_search_url(
        "https://www.indeed.com/q-acme-jobs.html",
        company_domain="acme.com",
    )
    assert not is_relevant_search_url(
        "https://internshala.com/company/wato-123/careers",
        company_domain="watolabs.com",
    )


def test_yc_company_page():
    assert is_relevant_search_url(
        "https://www.ycombinator.com/companies/wato",
        company_domain="watolabs.com",
        source_url="https://www.ycombinator.com/companies/wato",
        yc_slug="wato",
    )
    assert not is_relevant_search_url(
        "https://www.ycombinator.com/companies/other-co",
        company_domain="watolabs.com",
        source_url="https://www.ycombinator.com/companies/wato",
        yc_slug="wato",
    )


def test_filter_search_results():
    results = [
        SearchResult(url="https://evil.com/jobs", source="t", query_used="q"),
        SearchResult(url="https://acme.com/careers", source="t", query_used="q"),
    ]
    filtered = filter_search_results(results, company_domain="acme.com")
    assert len(filtered) == 1
    assert filtered[0].url == "https://acme.com/careers"
