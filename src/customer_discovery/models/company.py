from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator


def slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "unknown"


class TeamMember(BaseModel):
    name: str
    role: str | None = None
    linkedin_url: HttpUrl | str | None = None
    github_url: HttpUrl | str | None = None
    email: str | None = None


class ExternalLinks(BaseModel):
    linkedin: HttpUrl | str | None = None
    crunchbase: HttpUrl | str | None = None
    github: HttpUrl | str | None = None
    twitter: HttpUrl | str | None = None


class CompanyRecord(BaseModel):
    id: str
    name: str
    website: HttpUrl | str | None = None
    description: str | None = None
    industry: list[str] = Field(default_factory=list)
    batch: str | None = None
    program: str | None = None
    source: str
    source_url: HttpUrl | str | None = None
    team: list[TeamMember] = Field(default_factory=list)
    links: ExternalLinks = Field(default_factory=ExternalLinks)
    raw: dict[str, Any] = Field(default_factory=dict)
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("industry", mode="before")
    @classmethod
    def _coerce_industry(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v else []
        return list(v)

    @classmethod
    def make_id(cls, name: str, website: str | None) -> str:
        if website:
            from customer_discovery.pipeline.normalize import normalize_domain

            domain = normalize_domain(str(website))
            if domain:
                return slugify(domain)
        return slugify(name)

    def model_dump_json_schema(self) -> dict[str, Any]:
        return self.model_json_schema()


def company_json_schema() -> dict[str, Any]:
    return CompanyRecord.model_json_schema()
