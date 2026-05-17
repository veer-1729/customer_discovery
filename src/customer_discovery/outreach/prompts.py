from __future__ import annotations

import json
from typing import Any

from customer_discovery.models.company import CompanyRecord
from customer_discovery.models.evidence import EvidenceBundle
from customer_discovery.models.final import FinalBrief
from customer_discovery.models.outreach import OutreachContact
from customer_discovery.research.prompts import evidence_digest


def build_outreach_user_payload(
    *,
    company: CompanyRecord,
    brief: FinalBrief,
    bundle: EvidenceBundle | None,
    contact: OutreachContact,
    product: dict[str, Any],
    linkedin_max_chars: int,
) -> str:
    evidence = evidence_digest(bundle, max_items=20) if bundle else "(no evidence bundle)"
    return json.dumps(
        {
            "company_name": company.name,
            "website": str(company.website) if company.website else brief.website,
            "final_score": brief.final_score,
            "confidence": brief.confidence,
            "fit_label": brief.fit_label,
            "research_summary": brief.summary,
            "pain_points": brief.likely_pain_points,
            "disqualifiers": brief.disqualifiers,
            "seed_hook": brief.personalized_hook,
            "seed_discovery_question": brief.suggested_discovery_question,
            "positive_signals": [s.model_dump() for s in brief.positive_signals],
            "contact": contact.model_dump(),
            "important_urls": [u.model_dump() for u in brief.important_urls],
            "evidence": evidence,
            "product": product,
            "linkedin_max_chars": linkedin_max_chars,
        },
        indent=2,
    )
