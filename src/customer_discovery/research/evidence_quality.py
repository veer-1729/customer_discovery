from __future__ import annotations

from customer_discovery.models.evidence import EvidenceBundle, EvidenceItem
from customer_discovery.models.signals import ExtractedCompanySignals

MIN_EVIDENCE_SNIPPET_CHARS = 250


def count_rich_evidence_sources(items: list[EvidenceItem]) -> int:
    """Successful source types with enough text to be more than a SPA shell."""
    rich_types: set[str] = set()
    for item in items:
        if not item.success:
            continue
        if item.source_type in ("search_result", "fallback_page", "seed_metadata"):
            continue
        if len((item.text_snippet or "").strip()) >= MIN_EVIDENCE_SNIPPET_CHARS:
            rich_types.add(item.source_type)
    return len(rich_types)


def qualifies_for_premium_llm(
    bundle: EvidenceBundle,
    signals: ExtractedCompanySignals,
    *,
    min_rich_sources: int = 3,
) -> bool:
    if signals.hardware_heavy:
        return False
    if bundle.coverage.confidence_cap == "high":
        return True
    if count_rich_evidence_sources(bundle.items) >= min_rich_sources:
        return True
    return False
