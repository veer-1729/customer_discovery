from __future__ import annotations

from pydantic import BaseModel, Field


class DeterministicFitScore(BaseModel):
    company_id: str
    score: int = Field(ge=0, le=100)
    positive_rules: list[str] = Field(default_factory=list)
    negative_rules: list[str] = Field(default_factory=list)


def blend_triage_score(
    deterministic: int,
    llm_score: int,
    *,
    det_weight: float = 0.4,
    llm_weight: float = 0.6,
) -> int:
    blended = det_weight * deterministic + llm_weight * llm_score
    return max(0, min(100, int(round(blended))))
