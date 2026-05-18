#!/usr/bin/env python3
"""Live probe: evidence collection + link discovery for companies in companies.jsonl.

Usage:
  python scripts/probe_evidence.py --limit 3
  python scripts/probe_evidence.py --ids kelaicapital-com,watolabs-com
  python scripts/probe_evidence.py --limit 1 --with-search
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from customer_discovery.models.company import CompanyRecord
from customer_discovery.research.agents.evidence_collector import collect_evidence
from customer_discovery.research.agents.signal_extractor import extract_signals
from customer_discovery.research.config import load_research_config
from customer_discovery.research.tools import known_links
from customer_discovery.research.keywords import has_careers_signal, has_docs_signal
from customer_discovery.research.tools.search_fallback import SearchFallbackTool
from customer_discovery.storage.jsonl import read_jsonl

THIN_SNIPPET = 300


def _load_companies(path: Path, *, limit: int | None, ids: list[str] | None) -> list[CompanyRecord]:
    records = read_jsonl(path)
    if ids:
        wanted = set(ids)
        records = [r for r in records if r.id in wanted]
    elif limit is not None:
        records = records[:limit]
    return records


def _discovered_from_bundle(company: CompanyRecord, bundle, cfg: dict, cache_dir: Path) -> tuple[int, dict[str, list[str]]]:
    """Re-run known_links bucketing on the homepage item from a completed bundle."""
    from customer_discovery.research.fetch import extract_links

    homepage_item = next(
        (i for i in bundle.items if i.source_type == "homepage" and i.success),
        None,
    )
    if not homepage_item or not homepage_item.raw_cache_path:
        return 0, {k: [] for k in known_links.LINK_PATTERNS}

    path = Path(homepage_item.raw_cache_path)
    if not path.is_file():
        return 0, {k: [] for k in known_links.LINK_PATTERNS}

    base = homepage_item.url or str(company.website or "")
    html = path.read_text(encoding="utf-8", errors="replace")
    links = extract_links(html, base)
    discovered: dict[str, list[str]] = {k: [] for k in known_links.LINK_PATTERNS}
    for url, text in links:
        combined = f"{url} {text}"
        for kind, pat in known_links.LINK_PATTERNS.items():
            if pat.search(combined) and url not in discovered[kind]:
                discovered[kind].append(url)
    if company.links.github:
        gh = str(company.links.github)
        if gh not in discovered["github"]:
            discovered["github"].append(gh)
    return len(links), discovered


def _quality_note(item) -> str:
    if not item.success or not item.url:
        return ""
    snip = item.text_snippet or ""
    url = item.url.lower()
    if item.source_type == "careers":
        text_ok = has_careers_signal(snip)
        url_ok = "career" in url or "job" in url
        if len(snip) < THIN_SNIPPET and url_ok and not text_ok:
            return " [thin SPA shell; matched URL path only]"
        if not text_ok and not url_ok:
            return " [weak careers signal]"
    if item.source_type == "docs":
        if len(snip) < THIN_SNIPPET and not has_docs_signal(snip):
            return " [thin page; URL guess only]"
    return ""


def _print_report(
    company: CompanyRecord,
    discovered: dict[str, list[str]],
    bundle,
    signals,
    *,
    anchor_count: int,
) -> None:
    print("=" * 72)
    print(f"{company.name}  ({company.id})")
    print(f"  website: {company.website}")
    print(f"  homepage <a> tags in HTML: {anchor_count}")
    print()
    print("  Discovered from homepage <a> tags (known_links):")
    for kind, urls in discovered.items():
        if urls:
            print(f"    {kind}:")
            for u in urls[:8]:
                print(f"      - {u}")
    if not any(discovered.values()):
        print("    (none — homepage failed or no matching links in HTML)")
    print()
    print("  Evidence items collected:")
    for item in bundle.items:
        status = "ok" if item.success else f"FAIL: {item.error}"
        snip = len(item.text_snippet or "")
        url = item.url or "-"
        meta = ""
        if item.metadata.get("discovered_via"):
            meta = f" via={item.metadata['discovered_via']}"
        note = _quality_note(item)
        print(f"    [{item.source_type:16}] {status:12} snip={snip:5} {url}{meta}{note}")
    print()
    cov = bundle.coverage
    print(
        "  Coverage:",
        f"homepage={cov.homepage_found}",
        f"careers={cov.careers_found}",
        f"docs={cov.docs_found}",
        f"status={cov.status_found}",
        f"blog={cov.blog_or_changelog_found}",
        f"github={cov.github_found}",
        f"sources={cov.total_successful_sources}",
        f"cap={cov.confidence_cap}",
    )
    print(
        "  Signals:",
        f"b2b={signals.likely_b2b}",
        f"api_docs={signals.has_api_docs}",
        f"hiring_backend={signals.hiring_backend}",
        f"on_call={signals.mentions_on_call}",
        f"status_page={signals.has_status_page}",
    )
    if bundle.trace.failures:
        print("  Trace failures:", "; ".join(bundle.trace.failures[:5]))
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe evidence collection on real companies")
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "data" / "companies.jsonl",
    )
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--ids", type=str, default=None, help="Comma-separated company ids")
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=ROOT / "data" / "raw" / "research_probe",
    )
    parser.add_argument(
        "--with-search",
        action="store_true",
        help="Enable Tavily/search fallback (needs API key in env)",
    )
    args = parser.parse_args()

    ids = [x.strip() for x in args.ids.split(",")] if args.ids else None
    companies = _load_companies(args.input, limit=args.limit if not ids else None, ids=ids)
    if not companies:
        print("No companies matched.", file=sys.stderr)
        return 1

    cfg = load_research_config()
    SearchFallbackTool.configure(cfg, enabled=args.with_search)
    args.cache_dir.mkdir(parents=True, exist_ok=True)

    print(f"Probing {len(companies)} companies (search={'on' if args.with_search else 'off'})\n")

    for company in companies:
        bundle = collect_evidence(
            company,
            cfg,
            raw_cache_dir=args.cache_dir,
            search_enabled=args.with_search,
            force_refetch=False,
        )
        anchor_count, discovered = _discovered_from_bundle(
            company, bundle, cfg, args.cache_dir
        )
        signals = extract_signals(
            bundle,
            industries=company.industry,
            company_description=company.description,
        )
        _print_report(
            company, discovered, bundle, signals, anchor_count=anchor_count
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
