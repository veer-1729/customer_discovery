from __future__ import annotations

from pydantic import BaseModel, Field


class OutreachPack(BaseModel):
    """Part 3 output schema (stub — generation not implemented yet)."""

    company_id: str
    summary: str | None = None
    pain_points: list[str] = Field(default_factory=list)
    unique_selling_points: list[str] = Field(default_factory=list)
    hook_email: str | None = None
    hook_linkedin: str | None = None
    contact_role: str | None = None
    contact_name: str | None = None
    discovery_question: str | None = None
