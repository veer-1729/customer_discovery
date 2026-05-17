from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from customer_discovery.models.final import ImportantURL

ContactSource = Literal["seed_team", "seed_company_link", "persona_only"]


class OutreachContact(BaseModel):
    persona: str | None = None
    name: str | None = None
    title: str | None = None
    email: str | None = None
    linkedin_url: str | None = None
    contact_source: ContactSource = "persona_only"


class OutreachPack(BaseModel):
    company_id: str
    company_name: str
    website: str | None = None
    rank: int | None = None
    final_score: int = Field(default=0, ge=0, le=100)
    confidence: str = "low"
    final_stage: str = "triage"

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

    contact: OutreachContact = Field(default_factory=OutreachContact)
    important_urls: list[ImportantURL] = Field(default_factory=list)
    evidence_ids_used: list[str] = Field(default_factory=list)
    review_warnings: list[str] = Field(default_factory=list)
    ready_to_send: bool = False
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Legacy aliases for older code paths
    @property
    def summary(self) -> str:
        return self.company_summary

    @property
    def unique_selling_points(self) -> list[str]:
        return self.value_props_for_them

    @property
    def contact_role(self) -> str | None:
        return self.contact.persona

    @property
    def contact_name(self) -> str | None:
        return self.contact.name
