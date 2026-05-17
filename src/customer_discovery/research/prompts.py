from __future__ import annotations

import json
from typing import Any

from customer_discovery.models.evidence import EvidenceBundle
from customer_discovery.models.signals import ExtractedCompanySignals
from customer_discovery.models.scoring import DeterministicFitScore


def evidence_digest(bundle: EvidenceBundle, max_items: int = 12) -> str:
    lines = []
    for item in bundle.items:
        if not item.success:
            continue
        if len(lines) >= max_items:
            break
        snip = (item.text_snippet or "")[:1200]
        lines.append(
            f"[{item.id}] type={item.source_type} url={item.url or 'n/a'}\n{snip}\n"
        )
    return "\n---\n".join(lines) or "(no successful evidence)"


def build_triage_user_payload(
    *,
    company_name: str,
    website: str | None,
    source: str,
    bundle: EvidenceBundle,
    signals: ExtractedCompanySignals,
    det_score: DeterministicFitScore,
    product: dict[str, Any],
    icp: dict[str, Any],
) -> str:
    return json.dumps(
        {
            "company_name": company_name,
            "website": website,
            "source": source,
            "confidence_cap": bundle.coverage.confidence_cap,
            "deterministic_score": det_score.score,
            "deterministic_rules": {
                "positive": det_score.positive_rules,
                "negative": det_score.negative_rules,
            },
            "extracted_signals": signals.model_dump(),
            "coverage": bundle.coverage.model_dump(),
            "evidence": evidence_digest(bundle),
            "product": product,
            "icp_rubric": icp.get("prompt_rubric", ""),
        },
        indent=2,
    )
