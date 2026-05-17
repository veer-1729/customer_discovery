from __future__ import annotations

import csv
from pathlib import Path
from unittest.mock import patch

import pytest

from customer_discovery.models.company import CompanyRecord, TeamMember
from customer_discovery.models.final import FinalBrief
from customer_discovery.outreach.pipeline.orchestrator import OutreachOptions, OutreachOrchestrator
from customer_discovery.storage.staged_jsonl import append_staged
from customer_discovery.storage.jsonl import write_jsonl


@pytest.fixture
def outreach_env(tmp_path: Path) -> OutreachOptions:
    research = tmp_path / "research"
    research.mkdir()
    out = tmp_path / "outreach"
    out.mkdir()

    brief = FinalBrief(
        company_id="acme-com",
        company_name="Acme",
        website="https://acme.com",
        source="yc",
        final_score=85,
        confidence="high",
        fit_label="strong_candidate",
        summary="Test",
        best_contact_persona="founder",
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
                "final_score": "85",
                "confidence": "high",
                "final_stage": "premium",
                "fit_label": "strong_candidate",
                "manual_review_required": "false",
            }
        )

    write_jsonl(
        tmp_path / "companies.jsonl",
        [
            CompanyRecord(
                id="acme-com",
                name="Acme",
                website="https://acme.com",
                source="yc",
                team=[TeamMember(name="A", role="Founder")],
            )
        ],
    )

    return OutreachOptions(
        leads_path=research / "top_leads.csv",
        briefs_path=research / "final_briefs.jsonl",
        companies_path=tmp_path / "companies.jsonl",
        evidence_path=research / "evidence_bundles.jsonl",
        output_dir=out,
        cache_dir=tmp_path / "cache",
    )


def test_outreach_dry_run(outreach_env: OutreachOptions):
    orch = OutreachOrchestrator(outreach_env)
    outreach_env.dry_run = True
    stats = orch.run()
    assert stats["gated_count"] == 1


def test_outreach_run_mocked_llm(outreach_env: OutreachOptions):
    from customer_discovery.models.outreach import OutreachPack

    fake_pack = OutreachPack(
        company_id="acme-com",
        company_name="Acme",
        final_score=85,
        confidence="high",
        email_subject="S",
        email_body="B",
        ready_to_send=True,
    )

    with patch(
        "customer_discovery.outreach.pipeline.orchestrator.run_outreach_agent",
        return_value=fake_pack,
    ):
        stats = OutreachOrchestrator(outreach_env).run()

    assert stats["packs_written"] == 1
    assert (outreach_env.output_dir / "outreach_queue.csv").exists()
