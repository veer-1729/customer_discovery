from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from customer_discovery.models.company import CompanyRecord
from customer_discovery.models.final import FinalBrief
from customer_discovery.storage.jsonl import read_jsonl
from customer_discovery.storage.staged_jsonl import index_by_company


@dataclass
class GatedLead:
    company_id: str
    brief: FinalBrief
    company: CompanyRecord
    rank: int
    row: dict[str, str]


def _parse_bool(val: str) -> bool:
    return val.strip().lower() in ("true", "1", "yes")


def load_gated_leads(
    *,
    leads_path: Path,
    briefs_path: Path,
    companies_path: Path,
    cfg: dict[str, Any],
    min_score: int | None = None,
    top_n: int | None = None,
    include_manual_review: bool = False,
    company_id: str | None = None,
    limit: int | None = None,
) -> list[GatedLead]:
    if not leads_path.exists():
        raise FileNotFoundError(f"Missing leads file: {leads_path}. Run `customer-discovery research` first.")
    if not briefs_path.exists():
        raise FileNotFoundError(f"Missing briefs file: {briefs_path}")

    gates = cfg.get("gates", {})
    min_score = min_score if min_score is not None else gates.get("min_score", 70)
    top_n = top_n if top_n is not None else gates.get("top_n", 100)
    allowed_conf = set(gates.get("allowed_confidence", ["medium", "high"]))
    exclude_labels = set(gates.get("exclude_fit_labels", ["skip"]))
    exclude_manual = gates.get("exclude_manual_review", False) and not include_manual_review

    briefs = index_by_company(briefs_path, FinalBrief)
    companies = {c.id: c for c in read_jsonl(companies_path)} if companies_path.exists() else {}

    leads: list[GatedLead] = []
    with leads_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = row.get("company_id", "").strip()
            if not cid:
                for b in briefs.values():
                    if b.company_name == row.get("company_name"):
                        cid = b.company_id
                        break
            if not cid:
                continue
            if company_id and cid != company_id:
                continue
            brief = briefs.get(cid)
            if not brief:
                continue
            try:
                score = int(row.get("final_score", 0))
            except ValueError:
                score = 0
            if score < min_score:
                continue
            if row.get("fit_label") in exclude_labels:
                continue
            if row.get("confidence") not in allowed_conf:
                continue
            if exclude_manual and _parse_bool(row.get("manual_review_required", "false")):
                continue
            company = companies.get(cid)
            if not company:
                company = CompanyRecord(
                    id=cid,
                    name=brief.company_name,
                    website=brief.website,
                    source=brief.source,
                )
            try:
                rank = int(row.get("rank", 0))
            except ValueError:
                rank = 0
            leads.append(
                GatedLead(
                    company_id=cid,
                    brief=brief,
                    company=company,
                    rank=rank,
                    row=row,
                )
            )

    leads.sort(key=lambda x: x.rank or 9999)
    leads = leads[:top_n]
    if limit:
        leads = leads[:limit]
    return leads


def gate_stats(leads: list[GatedLead]) -> dict[str, Any]:
    with_name = sum(
        1
        for l in leads
        if l.company.team and any(m.name for m in l.company.team)
    )
    return {
        "gated_count": len(leads),
        "with_named_team_contact": with_name,
    }
