from __future__ import annotations

import csv
import json
from pathlib import Path

from customer_discovery.models.evidence import EvidenceBundle
from customer_discovery.models.final import FinalBrief
from customer_discovery.research.pipeline.url_catalog import best_url_by_type


CSV_COLUMNS = [
    "rank",
    "company_id",
    "company_name",
    "website",
    "source",
    "final_score",
    "confidence",
    "final_stage",
    "fit_label",
    "best_contact_persona",
    "personalized_hook",
    "suggested_discovery_question",
    "top_positive_signals",
    "top_negative_signals",
    "likely_pain_points",
    "disqualifiers",
    "manual_review_required",
    "important_urls",
    "homepage_url",
    "careers_url",
    "docs_url",
    "status_url",
    "github_url",
    "blog_or_changelog_url",
]


def rank_final_briefs(briefs: list[FinalBrief]) -> list[FinalBrief]:
    sorted_briefs = sorted(briefs, key=lambda b: b.final_score, reverse=True)
    for i, b in enumerate(sorted_briefs, start=1):
        b.rank = i
    return sorted_briefs


def write_top_leads_csv(
    path: Path,
    briefs: list[FinalBrief],
    bundles: dict[str, EvidenceBundle],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ranked = rank_final_briefs(briefs)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for b in ranked:
            bundle = bundles.get(b.company_id)
            writer.writerow(_row(b, bundle))


def _row(b: FinalBrief, bundle: EvidenceBundle | None) -> dict[str, str]:
    pos = "; ".join(s.claim for s in b.positive_signals[:5])
    neg = "; ".join(s.claim for s in b.negative_signals[:5])
    pains = "; ".join(b.likely_pain_points[:5])
    disq = "; ".join(b.disqualifiers[:5])
    urls_json = json.dumps([u.model_dump() for u in b.important_urls])
    homepage = careers = docs = status = github = blog = ""
    if bundle:
        homepage = best_url_by_type(bundle, "homepage")
        careers = best_url_by_type(bundle, "careers")
        docs = best_url_by_type(bundle, "docs")
        status = best_url_by_type(bundle, "status")
        github = best_url_by_type(bundle, "github")
        blog = best_url_by_type(bundle, "blog") or best_url_by_type(bundle, "changelog")
    return {
        "rank": str(b.rank or ""),
        "company_id": b.company_id,
        "company_name": b.company_name,
        "website": b.website or "",
        "source": b.source,
        "final_score": str(b.final_score),
        "confidence": b.confidence,
        "final_stage": b.final_stage,
        "fit_label": b.fit_label,
        "best_contact_persona": b.best_contact_persona or "",
        "personalized_hook": b.personalized_hook or "",
        "suggested_discovery_question": b.suggested_discovery_question or "",
        "top_positive_signals": pos,
        "top_negative_signals": neg,
        "likely_pain_points": pains,
        "disqualifiers": disq,
        "manual_review_required": str(b.manual_review_required).lower(),
        "important_urls": urls_json,
        "homepage_url": homepage,
        "careers_url": careers,
        "docs_url": docs,
        "status_url": status,
        "github_url": github,
        "blog_or_changelog_url": blog,
    }
