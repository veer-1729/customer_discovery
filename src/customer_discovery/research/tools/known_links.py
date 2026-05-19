from __future__ import annotations

import re
from urllib.parse import urlparse

from customer_discovery.research.fetch import extract_links
from customer_discovery.research.tools.base import ToolContext


LINK_PATTERNS: dict[str, re.Pattern[str]] = {
    "careers": re.compile(r"career|jobs?|hiring|join-?us|work-?with", re.I),
    "docs": re.compile(r"docs?|developer|api|documentation", re.I),
    "status": re.compile(r"status|uptime|health", re.I),
    "github": re.compile(r"github\.com", re.I),
    "blog": re.compile(r"blog|news|changelog|updates", re.I),
    "team": re.compile(r"\bteam\b|about-?us|our-?people|leadership|founders?", re.I),
    "pricing": re.compile(r"pricing|plans?|subscribe", re.I),
    "features": re.compile(r"features?|product|platform|solutions?", re.I),
    "contact": re.compile(r"contact|get-?in-?touch|reach-?us", re.I),
    "faq": re.compile(r"\bfaq\b|frequently-?asked|help-?center|support", re.I),
    "services": re.compile(r"services?|offerings?|what-we-do", re.I),
}


def run_known_links_extract(ctx: ToolContext) -> None:
    homepage = next((i for i in ctx.items if i.source_type == "homepage" and i.success), None)
    if not homepage or not homepage.raw_cache_path:
        return
    from pathlib import Path

    html = Path(homepage.raw_cache_path).read_text(encoding="utf-8", errors="replace")
    base = homepage.url or ctx.website or ""
    if not base:
        return
    links = extract_links(html, base)
    discovered: dict[str, list[str]] = {k: [] for k in LINK_PATTERNS}
    for url, text in links:
        combined = f"{url} {text}"
        for kind, pat in LINK_PATTERNS.items():
            if pat.search(combined) and url not in discovered[kind]:
                discovered[kind].append(url)
    if ctx.company.links.github:
        gh = str(ctx.company.links.github)
        if gh not in discovered["github"]:
            discovered["github"].append(gh)
    ctx.discovered_links = discovered


def pick_links(ctx: ToolContext, kind: str) -> list[str]:
    return ctx.discovered_links.get(kind, [])
