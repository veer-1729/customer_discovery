from __future__ import annotations

import csv
import json
from pathlib import Path

from customer_discovery.models.outreach import OutreachPack

QUEUE_COLUMNS = [
    "rank",
    "company_id",
    "company_name",
    "website",
    "final_score",
    "confidence",
    "ready_to_send",
    "review_warnings",
    "contact_persona",
    "contact_name",
    "contact_title",
    "contact_email",
    "contact_linkedin",
    "contact_source",
    "email_subject",
    "email_body",
    "linkedin_connection_note",
    "discovery_question",
    "homepage_url",
    "careers_url",
    "docs_url",
    "important_urls",
    "all_scraped_urls",
]


def write_outreach_queue(path: Path, packs: list[OutreachPack]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sorted_packs = sorted(packs, key=lambda p: p.rank or 9999)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=QUEUE_COLUMNS)
        writer.writeheader()
        for p in sorted_packs:
            writer.writerow(_queue_row(p))


def _queue_row(p: OutreachPack) -> dict[str, str]:
    urls_by_type = {u.source_type: u.url for u in p.important_urls}
    all_urls = "; ".join(u.url for u in p.important_urls)
    return {
        "rank": str(p.rank or ""),
        "company_id": p.company_id,
        "company_name": p.company_name,
        "website": p.website or "",
        "final_score": str(p.final_score),
        "confidence": p.confidence,
        "ready_to_send": str(p.ready_to_send).lower(),
        "review_warnings": "; ".join(p.review_warnings),
        "contact_persona": p.contact.persona or "",
        "contact_name": p.contact.name or "",
        "contact_title": p.contact.title or "",
        "contact_email": p.contact.email or "",
        "contact_linkedin": p.contact.linkedin_url or "",
        "contact_source": p.contact.contact_source,
        "email_subject": p.email_subject or "",
        "email_body": p.email_body or "",
        "linkedin_connection_note": p.linkedin_connection_note or "",
        "discovery_question": p.discovery_question or "",
        "homepage_url": urls_by_type.get("homepage", ""),
        "careers_url": urls_by_type.get("careers", ""),
        "docs_url": urls_by_type.get("docs", ""),
        "important_urls": json.dumps([u.model_dump() for u in p.important_urls]),
        "all_scraped_urls": all_urls,
    }
