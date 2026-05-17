from __future__ import annotations

from typing import Any

from customer_discovery.models.company import CompanyRecord, TeamMember
from customer_discovery.models.outreach import OutreachContact

PERSONA_ALIASES = {
    "technical founder": "technical_founder",
    "founder": "technical_founder",
    "cto": "cto",
    "backend": "backend_engineer",
    "platform": "platform_engineer",
    "sre": "platform_engineer",
    "devops": "platform_engineer",
}


def _normalize_persona(persona: str | None) -> str | None:
    if not persona:
        return None
    p = persona.lower()
    for key, canonical in PERSONA_ALIASES.items():
        if key in p:
            return canonical
    return None


def _score_member(member: TeamMember, keywords: list[str]) -> int:
    text = " ".join(
        filter(None, [member.role or "", member.name or ""])
    ).lower()
    return sum(1 for kw in keywords if kw in text)


def select_contact(
    company: CompanyRecord,
    persona: str | None,
    cfg: dict[str, Any],
) -> OutreachContact:
    contact_cfg = cfg.get("contact", {})
    keywords_map: dict[str, list[str]] = contact_cfg.get("persona_role_keywords", {})
    canonical = _normalize_persona(persona)
    keywords = keywords_map.get(canonical or "", []) if canonical else []

    best: TeamMember | None = None
    best_score = 0
    for member in company.team:
        score = _score_member(member, keywords) if keywords else 0
        if not keywords and member.role:
            score = 1
        if score > best_score:
            best_score = score
            best = member

    if best and best.name:
        return OutreachContact(
            persona=persona,
            name=best.name,
            title=best.role,
            email=best.email,
            linkedin_url=str(best.linkedin_url) if best.linkedin_url else None,
            contact_source="seed_team",
        )

    if company.links.linkedin:
        return OutreachContact(
            persona=persona,
            linkedin_url=str(company.links.linkedin),
            contact_source="seed_company_link",
        )

    return OutreachContact(persona=persona, contact_source="persona_only")


def contact_warnings(contact: OutreachContact) -> list[str]:
    warnings: list[str] = []
    if contact.contact_source == "persona_only":
        warnings.append("no_seed_contact")
    if not contact.email:
        warnings.append("no_seed_email")
    if not contact.linkedin_url and contact.contact_source != "seed_team":
        warnings.append("no_linkedin_url")
    return warnings
