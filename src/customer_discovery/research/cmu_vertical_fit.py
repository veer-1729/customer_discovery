from __future__ import annotations

# CMU Airtable vertical tags that suggest production software / SRE-relevant customers.
STRONG_VERTICAL_TERMS = (
    "ai/ml",
    "artificial intelligence",
    "enterprise software",
    "saas",
    "devtools",
    "developer tools",
    "infrastructure",
    "cloud",
    "fintech",
    "cybersecurity",
    "security",
    "data platform",
    "api",
    "b2b",
    "platform",
    "martech",
    "hr tech",
    "edtech",
)

WEAK_VERTICAL_TERMS = (
    "consumer",
    "retail",
    "food",
    "fashion",
    "media",
    "entertainment",
)


def score_vertical_alignment(industries: list[str]) -> tuple[int, list[str], list[str]]:
    """Bonus/penalty from CMU Verticals metadata (Part 2 scoring, not scrape filters)."""
    if not industries:
        return 0, [], []
    blob = " ".join(industries).lower()
    positive: list[str] = []
    negative: list[str] = []
    score = 0

    strong_hits = [t for t in STRONG_VERTICAL_TERMS if t in blob]
    if strong_hits:
        score += min(15, 8 + 2 * len(strong_hits))
        positive.append("cmu_vertical_software_aligned")

    weak_hits = [t for t in WEAK_VERTICAL_TERMS if t in blob]
    if weak_hits and not strong_hits:
        score -= 10
        negative.append("cmu_vertical_consumer_or_non_software")

    return score, positive, negative
