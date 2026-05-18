from __future__ import annotations

from typing import Any

from customer_discovery.models.signals import ExtractedCompanySignals
from customer_discovery.models.triage import FitLabel


def merge_disqualifiers(
    llm_disqualifiers: list[str],
    signals: ExtractedCompanySignals,
    product: dict[str, Any],
) -> list[str]:
    out: list[str] = list(llm_disqualifiers)
    for d in product.get("disqualifiers") or []:
        if signals.hardware_heavy and "hardware" in d.lower() and d not in out:
            out.append(d)
    if signals.hardware_heavy and "hardware_heavy" not in " ".join(out).lower():
        out.append("Hardware-heavy company (physical product / industrial focus)")
    return out


def align_fit_label(
    label: str,
    triage_score: int,
    signals: ExtractedCompanySignals,
) -> FitLabel:
    """Keep fit_label consistent with blended score and hard signals."""
    if label not in ("skip", "maybe", "strong_candidate", "needs_review"):
        label = "maybe"

    if signals.hardware_heavy:
        if triage_score < 50:
            return "skip"
        return "needs_review"

    if triage_score < 50:
        return "skip"
    if triage_score < 65:
        return "maybe" if label == "strong_candidate" else label  # type: ignore[return-value]
    if triage_score < 75 and label == "strong_candidate":
        return "needs_review"
    if (
        triage_score >= 75
        and label in ("maybe", "needs_review")
        and signals.likely_b2b
        and signals.has_ops_evidence
        and not signals.hardware_heavy
    ):
        return "strong_candidate"
    return label  # type: ignore[return-value]
