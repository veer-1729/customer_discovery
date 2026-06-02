from __future__ import annotations

import re

# Physical-product / industrial-hardware language (not "robotics platform" alone).
HARDWARE_STRONG = re.compile(
    r"\b("
    r"robotic\s+weld|welding\s+robot|weld(?:ing)?\s+system|"
    r"metal\s+fabricat|industrial\s+robot(?:ics)?(?!\s+software)|"
    r"CNC\s+machin|semiconductor\s+fab|"
    r"aerospace\s+(?:hardware|systems)|defense\s+contractor|"
    r"hardware\s+product|physical\s+product|"
    r"manufacturing\s+equipment|industrial\s+automation\s+system"
    r")\b",
    re.I,
)

# Signals the company sells software / platform (keeps robotics-SaaS in play).
SOFTWARE_COUNTER = re.compile(
    r"\b("
    r"software\s+(?:for|platform|that)|"
    r"saas|devtools|developer\s+tools|"
    r"api\s+(?:platform|reference|docs)|developer\s+docs|"
    r"cloud\s+platform|workflow\s+(?:software|automation)|"
    r"orchestration\s+layer|enterprise\s+software|"
    r"next\s+generation\s+of\s+software|"
    r"ai\s+(?:platform|infrastructure|agents?)"
    r")\b",
    re.I,
)

HARDWARE_INDUSTRY_TERMS = (
    "hardware",
    "robotics",
    "manufacturing",
    "industrial automation",
    "aerospace",
    "defense",
    "drones",
    "automotive",
    "medical device",
    "construction",
    "energy",
    "mining",
    "agriculture",
    "agritech",
    "farming",
    "aquaculture",
)

SOFTWARE_INDUSTRY_TERMS = (
    "software",
    "saas",
    "developer tools",
    "devtools",
    "b2b",
    "enterprise",
    "artificial intelligence",
    "generative ai",
    "machine learning",
    "fintech",
    "infrastructure",
    "api",
)

MIN_SUBSTANTIVE_DOCS_CHARS = 400


def industry_suggests_hardware(industries: list[str]) -> bool:
    """YC industry tags skew hardware-only (not robotics + SaaS)."""
    if not industries:
        return False
    blob = " ".join(industries).lower()
    has_hw = any(term in blob for term in HARDWARE_INDUSTRY_TERMS)
    has_sw = any(term in blob for term in SOFTWARE_INDUSTRY_TERMS)
    return has_hw and not has_sw


def text_suggests_hardware_heavy(*texts: str) -> bool:
    combined = " ".join(t for t in texts if t)
    if not combined.strip():
        return False
    if SOFTWARE_COUNTER.search(combined):
        return False
    return bool(HARDWARE_STRONG.search(combined))


def is_hardware_heavy(
    *,
    industries: list[str],
    homepage_text: str = "",
    description: str = "",
    seed_text: str = "",
) -> bool:
    if industry_suggests_hardware(industries):
        combined = " ".join([homepage_text, description, seed_text])
        if SOFTWARE_COUNTER.search(combined):
            return False
        return True
    return text_suggests_hardware_heavy(homepage_text, description, seed_text)


def has_substantive_docs_text(docs_text: str) -> bool:
    from customer_discovery.research.keywords import has_docs_signal

    text = (docs_text or "").strip()
    return len(text) >= MIN_SUBSTANTIVE_DOCS_CHARS and has_docs_signal(text)


def has_ops_evidence(*, mentions_on_call: bool, has_substantive_docs: bool) -> bool:
    """On-call language or real developer-docs content (not empty /docs paths)."""
    return mentions_on_call or has_substantive_docs
