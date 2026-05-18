from __future__ import annotations

from customer_discovery.models.evidence import EvidenceBundle, EvidenceItem
from customer_discovery.models.signals import ExtractedCompanySignals
from customer_discovery.research.hardware_fit import (
    has_ops_evidence,
    has_substantive_docs_text,
    is_hardware_heavy,
)
from customer_discovery.research.keywords import (
    B2B_KEYWORDS,
    CONSUMER_KEYWORDS,
    HIRING_BACKEND,
    HIRING_PLATFORM,
    NEGATIVE_MATURE_SRE,
    NEGATIVE_PRELAUNCH,
    ON_CALL_KEYWORDS,
    has_docs_signal,
)


def _text_for_types(items: list[EvidenceItem], types: set[str]) -> str:
    parts = [i.text_snippet for i in items if i.success and i.source_type in types]
    return " ".join(parts)


def extract_signals(
    bundle: EvidenceBundle,
    *,
    industries: list[str] | None = None,
    company_description: str | None = None,
) -> ExtractedCompanySignals:
    items = bundle.items
    all_text = " ".join(i.text_snippet for i in items if i.success)
    careers_text = _text_for_types(items, {"careers"})
    docs_text = _text_for_types(items, {"docs"})
    homepage_text = _text_for_types(items, {"homepage", "seed_metadata"})

    refs: list[str] = []
    negatives: list[str] = []

    def add_ref(item: EvidenceItem | None) -> None:
        if item and item.id not in refs:
            refs.append(item.id)

    likely_b2b = bool(B2B_KEYWORDS.search(homepage_text + docs_text))
    likely_consumer = bool(CONSUMER_KEYWORDS.search(homepage_text)) and not likely_b2b
    has_substantive_docs = has_substantive_docs_text(docs_text)
    has_api = has_substantive_docs or (
        has_docs_signal(docs_text) and len(docs_text.strip()) >= 200
    )
    has_webhooks = "webhook" in docs_text.lower()
    has_integrations = "integration" in (docs_text + all_text).lower()
    has_status = bundle.coverage.status_found
    hiring_backend = bool(HIRING_BACKEND.search(careers_text))
    hiring_platform = bool(HIRING_PLATFORM.search(careers_text))
    hiring_infra = hiring_platform or "sre" in careers_text.lower()
    on_call = bool(ON_CALL_KEYWORDS.search(careers_text + all_text))
    incident = "incident" in all_text.lower()
    ops_evidence = has_ops_evidence(
        mentions_on_call=on_call,
        has_substantive_docs=has_substantive_docs,
    )
    production_critical = likely_b2b and ops_evidence

    seed_text = _text_for_types(items, {"seed_metadata"})
    hardware_heavy = is_hardware_heavy(
        industries=industries or [],
        homepage_text=homepage_text,
        description=company_description or "",
        seed_text=seed_text,
    )
    if hardware_heavy:
        negatives.append("hardware_heavy")

    if NEGATIVE_PRELAUNCH.search(homepage_text):
        negatives.append("pre_launch_signals")
    if NEGATIVE_MATURE_SRE.search(all_text):
        negatives.append("mature_sre_org_signals")
    if likely_consumer:
        negatives.append("consumer_only_signals")
    if not bundle.website:
        negatives.append("no_website")

    for item in items:
        if item.success and item.source_type in ("careers", "docs", "homepage"):
            add_ref(item)

    return ExtractedCompanySignals(
        company_id=bundle.company_id,
        company_name=bundle.company_name,
        likely_b2b=likely_b2b,
        likely_consumer=likely_consumer,
        has_api_docs=has_api,
        has_webhooks=has_webhooks,
        has_integrations=has_integrations,
        has_status_page=has_status,
        hiring_backend=hiring_backend,
        hiring_platform=hiring_platform,
        hiring_infra_sre=hiring_infra,
        mentions_on_call=on_call,
        mentions_incident_response=incident,
        likely_production_critical=production_critical,
        hardware_heavy=hardware_heavy,
        has_substantive_docs=has_substantive_docs,
        has_ops_evidence=ops_evidence,
        negative_signals_detected=negatives,
        evidence_refs=refs,
    )
