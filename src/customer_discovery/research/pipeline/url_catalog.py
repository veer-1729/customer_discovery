from __future__ import annotations

from customer_discovery.models.evidence import EvidenceBundle, EvidenceItem
from customer_discovery.models.final import ImportantURL
from customer_discovery.models.premium import PremiumBrief

WHY_TEMPLATES: dict[str, str] = {
    "homepage": "Explains core product and target customer.",
    "careers": "Contains hiring/on-call/reliability signals.",
    "docs": "Shows public API/integration/developer surface.",
    "status": "Indicates production uptime monitoring.",
    "github": "Technical footprint and engineering culture.",
    "blog": "Product updates and engineering narrative.",
    "changelog": "Release discipline and operational change signals.",
    "seed_metadata": "Source list metadata (YC/CMU).",
    "search_result": "Discovered via web search fallback.",
    "fallback_page": "Fetched from search result for additional context.",
}

# Prefer these types when the same URL appears on multiple evidence items
SOURCE_TYPE_PRIORITY = [
    "homepage",
    "careers",
    "docs",
    "status",
    "github",
    "blog",
    "changelog",
    "seed_metadata",
    "fallback_page",
    "search_result",
]


def _normalize_url(url: str) -> str:
    return url.strip().rstrip("/").lower()


def _why_for_item(
    item: EvidenceItem,
    url_notes: dict[str, str],
) -> str:
    if item.url and item.url in url_notes:
        return url_notes[item.url]
    base = WHY_TEMPLATES.get(item.source_type, "Public page collected during evidence gathering.")
    if not item.success and item.error:
        return f"{base} (fetch failed: {item.error})"
    return base


def _pick_canonical_item(items: list[EvidenceItem]) -> EvidenceItem:
    """When multiple evidence rows share a URL, prefer highest-priority source_type."""

    def rank(it: EvidenceItem) -> int:
        try:
            return SOURCE_TYPE_PRIORITY.index(it.source_type)
        except ValueError:
            return len(SOURCE_TYPE_PRIORITY)

    return sorted(items, key=rank)[0]


def build_important_urls(
    bundle: EvidenceBundle,
    evidence_ids_used: list[str],
    *,
    premium: PremiumBrief | None = None,
) -> list[ImportantURL]:
    """Include every URL the evidence agent recorded (all EvidenceItems + trace attempts)."""
    used_set = set(evidence_ids_used)
    url_notes = {n.url: n.why_important for n in (premium.url_notes if premium else [])}

    by_url: dict[str, list[EvidenceItem]] = {}
    for item in bundle.items:
        if not item.url:
            continue
        key = _normalize_url(item.url)
        by_url.setdefault(key, []).append(item)

    urls: list[ImportantURL] = []
    for _key, group in sorted(by_url.items(), key=lambda kv: kv[1][0].url or ""):
        item = _pick_canonical_item(group)
        used = any(i.id in used_set for i in group)
        urls.append(
            ImportantURL(
                url=item.url or "",
                source_type=item.source_type,
                why_important=_why_for_item(item, url_notes),
                used_in_reasoning=used,
            )
        )

    seen_keys = set(by_url.keys())
    for raw_url in bundle.trace.urls_attempted:
        if not raw_url:
            continue
        key = _normalize_url(raw_url)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        urls.append(
            ImportantURL(
                url=raw_url,
                source_type="fallback_page",
                why_important="URL probed during evidence collection (see trace).",
                used_in_reasoning=False,
            )
        )

    return urls


def all_evidence_urls(bundle: EvidenceBundle) -> list[str]:
    """Ordered unique URLs from bundle (for exports)."""
    return [u.url for u in build_important_urls(bundle, [])]


def best_url_by_type(bundle: EvidenceBundle, source_type: str) -> str:
    for item in bundle.items:
        if item.success and item.source_type == source_type and item.url:
            return item.url
    if source_type == "blog":
        for item in bundle.items:
            if item.success and item.source_type == "changelog" and item.url:
                return item.url
    return ""
