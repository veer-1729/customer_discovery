from __future__ import annotations

from pydantic import BaseModel, Field


class EvidenceBackedSignal(BaseModel):
    claim: str
    evidence_ids: list[str] = Field(default_factory=list)


class ExtractedCompanySignals(BaseModel):
    company_id: str
    company_name: str
    likely_b2b: bool = False
    likely_consumer: bool = False
    has_api_docs: bool = False
    has_webhooks: bool = False
    has_integrations: bool = False
    has_status_page: bool = False
    hiring_backend: bool = False
    hiring_platform: bool = False
    hiring_infra_sre: bool = False
    mentions_on_call: bool = False
    mentions_incident_response: bool = False
    likely_production_critical: bool = False
    negative_signals_detected: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    raw_keywords: dict[str, list[str]] = Field(default_factory=dict)


class SignalRecord(BaseModel):
    """Row in signals.jsonl: signals + deterministic score."""

    company_id: str
    signals: ExtractedCompanySignals
    deterministic_score: int
    positive_rules: list[str] = Field(default_factory=list)
    negative_rules: list[str] = Field(default_factory=list)
