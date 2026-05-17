from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from customer_discovery.models.company import CompanyRecord
from customer_discovery.models.evidence import EvidenceBundle
from customer_discovery.models.final import FinalBrief
from customer_discovery.models.outreach import OutreachContact, OutreachPack
from customer_discovery.outreach.contact_selector import contact_warnings
from customer_discovery.outreach.prompts import build_outreach_user_payload
from customer_discovery.llm.client import LLMClient
from customer_discovery.research.pipeline.url_catalog import build_important_urls


class OutreachLLMOutput(BaseModel):
    company_summary: str = ""
    pain_points: list[str] = Field(default_factory=list)
    value_props_for_them: list[str] = Field(default_factory=list)
    disqualifier_notes: list[str] = Field(default_factory=list)
    hook_email: str | None = None
    hook_linkedin: str | None = None
    email_subject: str | None = None
    email_body: str | None = None
    linkedin_connection_note: str | None = None
    discovery_question: str | None = None


OUTREACH_SYSTEM = """You prepare outreach drafts for B2B customer discovery.
Rules:
- Direct, technical, not salesy (see product.outreach_tone).
- Use only facts from the research summary and evidence; do not invent customers or features.
- If contact.name is set, use it in the greeting; otherwise use role-based greeting without inventing a name.
- email_body: about 120-180 words, one clear discovery_question at the end.
- linkedin_connection_note: MUST be at most linkedin_max_chars characters.
- Polish seed_hook if provided; do not contradict it.
Output valid JSON only."""


def run_outreach_agent(
    *,
    company: CompanyRecord,
    brief: FinalBrief,
    bundle: EvidenceBundle | None,
    contact: OutreachContact,
    llm: LLMClient,
    model: str,
    product: dict[str, Any],
    linkedin_max_chars: int,
    rank: int | None = None,
) -> OutreachPack:
    user = build_outreach_user_payload(
        company=company,
        brief=brief,
        bundle=bundle,
        contact=contact,
        product=product,
        linkedin_max_chars=linkedin_max_chars,
    )
    out = llm.complete_json(
        model=model,
        system=OUTREACH_SYSTEM,
        user=user,
        schema=OutreachLLMOutput,
    )

    if out.linkedin_connection_note and len(out.linkedin_connection_note) > linkedin_max_chars:
        out.linkedin_connection_note = out.linkedin_connection_note[: linkedin_max_chars - 3] + "..."

    important_urls = brief.important_urls
    if bundle:
        important_urls = build_important_urls(bundle, brief.evidence_ids_used)

    warnings = list(brief.manual_review_required and ["manual_review_required"] or [])
    warnings.extend(contact_warnings(contact))

    ready = bool(
        out.email_body
        and out.email_subject
        and contact.contact_source != "persona_only"
        and not brief.manual_review_required
    )

    return OutreachPack(
        company_id=company.id,
        company_name=company.name,
        website=str(company.website) if company.website else brief.website,
        rank=rank or brief.rank,
        final_score=brief.final_score,
        confidence=brief.confidence,
        final_stage=brief.final_stage,
        company_summary=out.company_summary or brief.summary,
        pain_points=out.pain_points or brief.likely_pain_points,
        value_props_for_them=out.value_props_for_them,
        disqualifier_notes=out.disqualifier_notes or brief.disqualifiers,
        hook_email=out.hook_email,
        hook_linkedin=out.hook_linkedin,
        email_subject=out.email_subject,
        email_body=out.email_body,
        linkedin_connection_note=out.linkedin_connection_note,
        discovery_question=out.discovery_question or brief.suggested_discovery_question,
        contact=contact,
        important_urls=important_urls,
        evidence_ids_used=brief.evidence_ids_used,
        review_warnings=warnings,
        ready_to_send=ready,
    )
