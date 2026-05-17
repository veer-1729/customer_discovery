from __future__ import annotations

import csv
from pathlib import Path

import pytest

from customer_discovery.models.company import CompanyRecord, TeamMember
from customer_discovery.models.final import FinalBrief
from customer_discovery.models.outreach import OutreachPack
from customer_discovery.outreach.contact_selector import contact_warnings, select_contact
from customer_discovery.outreach.pipeline.gate import load_gated_leads
from customer_discovery.outreach.agents.outreach_agent import run_outreach_agent
from customer_discovery.llm.client import MockLLMClient
from customer_discovery.storage.staged_jsonl import append_staged


@pytest.fixture
def fixture_dir(tmp_path: Path) -> Path:
    research = tmp_path / "research"
    research.mkdir()
    brief = FinalBrief(
        company_id="acme-com",
        company_name="Acme",
        website="https://acme.com",
        source="yc",
        final_score=80,
        confidence="high",
        final_stage="premium",
        fit_label="strong_candidate",
        summary="B2B API platform",
        best_contact_persona="technical founder",
        personalized_hook="Seed hook",
        suggested_discovery_question="How do you handle incidents?",
        manual_review_required=False,
    )
    append_staged(research / "final_briefs.jsonl", brief)

    with (research / "top_leads.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "rank",
                "company_id",
                "company_name",
                "website",
                "source",
                "final_score",
                "confidence",
                "final_stage",
                "fit_label",
                "manual_review_required",
            ],
        )
        w.writeheader()
        w.writerow(
            {
                "rank": "1",
                "company_id": "acme-com",
                "company_name": "Acme",
                "website": "https://acme.com",
                "source": "yc",
                "final_score": "80",
                "confidence": "high",
                "final_stage": "premium",
                "fit_label": "strong_candidate",
                "manual_review_required": "false",
            }
        )

    company = CompanyRecord(
        id="acme-com",
        name="Acme",
        website="https://acme.com",
        source="yc",
        team=[TeamMember(name="Jane Doe", role="Co-founder & CTO")],
    )
    from customer_discovery.storage.jsonl import write_jsonl

    write_jsonl(tmp_path / "companies.jsonl", [company])
    return tmp_path


def test_select_contact_from_team():
    company = CompanyRecord(
        id="x",
        name="X",
        source="yc",
        team=[TeamMember(name="Jane", role="CTO and Co-founder")],
    )
    c = select_contact(company, "technical founder", {"contact": {"persona_role_keywords": {"technical_founder": ["founder", "cto"]}}})
    assert c.name == "Jane"
    assert c.contact_source == "seed_team"


def test_select_contact_persona_only():
    company = CompanyRecord(id="x", name="X", source="yc")
    c = select_contact(company, "platform engineer", {})
    assert c.contact_source == "persona_only"
    assert "no_seed_contact" in contact_warnings(c)


def test_gate_loads_leads(fixture_dir: Path):
    leads = load_gated_leads(
        leads_path=fixture_dir / "research" / "top_leads.csv",
        briefs_path=fixture_dir / "research" / "final_briefs.jsonl",
        companies_path=fixture_dir / "companies.jsonl",
        cfg={"gates": {"min_score": 70, "top_n": 10, "allowed_confidence": ["high"], "exclude_fit_labels": ["skip"]}},
    )
    assert len(leads) == 1
    assert leads[0].company_id == "acme-com"


def test_outreach_agent_mock():
    company = CompanyRecord(
        id="acme-com",
        name="Acme",
        website="https://acme.com",
        source="yc",
        team=[TeamMember(name="Jane", role="Founder")],
    )
    brief = FinalBrief(
        company_id="acme-com",
        company_name="Acme",
        final_score=80,
        confidence="high",
        summary="API company",
        personalized_hook="hook",
    )
    llm = MockLLMClient(
        {
            "OutreachLLMOutput": {
                "company_summary": "API company",
                "email_subject": "Hi",
                "email_body": "Body text here.",
                "linkedin_connection_note": "Short note",
                "discovery_question": "Q?",
            }
        }
    )
    pack = run_outreach_agent(
        company=company,
        brief=brief,
        bundle=None,
        contact=select_contact(company, "founder", {}),
        llm=llm,
        model="gpt-4o-mini",
        product={"outreach_tone": "technical"},
        linkedin_max_chars=300,
    )
    assert pack.email_subject == "Hi"
    assert pack.contact.name == "Jane"
    assert isinstance(pack, OutreachPack)
