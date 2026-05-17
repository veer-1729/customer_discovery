from __future__ import annotations

import re

CAREERS_KEYWORDS = re.compile(
    r"\b(careers?|jobs?|hiring|open roles?|we're hiring|join our team|"
    r"backend engineer|platform engineer|sre|devops|infrastructure engineer|"
    r"on-?call|oncall|incident response|reliability engineer)\b",
    re.I,
)

DOCS_KEYWORDS = re.compile(
    r"\b(api reference|api docs|developer docs|rest api|graphql|webhooks?|"
    r"integrations?|authentication|oauth|sdk)\b",
    re.I,
)

B2B_KEYWORDS = re.compile(
    r"\b(enterprise|b2b|saas|developers?|customers?|teams?|platform|"
    r"infrastructure|api|integration)\b",
    re.I,
)

CONSUMER_KEYWORDS = re.compile(
    r"\b(consumer|mobile app|social network|dating app|game|entertainment)\b",
    re.I,
)

ON_CALL_KEYWORDS = re.compile(
    r"\b(on-?call|oncall|pagerduty|incident|postmortem|root cause|sla|uptime|"
    r"production ownership|reliability)\b",
    re.I,
)

HIRING_BACKEND = re.compile(
    r"\b(backend|full[- ]stack|software engineer|platform engineer)\b",
    re.I,
)

HIRING_PLATFORM = re.compile(
    r"\b(platform|infrastructure|devops|sre|site reliability)\b",
    re.I,
)

NEGATIVE_PRELAUNCH = re.compile(
    r"\b(coming soon|waitlist|pre-?launch|stealth mode|not yet launched)\b",
    re.I,
)

NEGATIVE_MATURE_SRE = re.compile(
    r"\b(dedicated sre team|24/7 noc|global reliability org)\b",
    re.I,
)


def has_careers_signal(text: str) -> bool:
    return bool(CAREERS_KEYWORDS.search(text))


def has_docs_signal(text: str) -> bool:
    return bool(DOCS_KEYWORDS.search(text))
