from __future__ import annotations

import enum
from typing import Any

from pydantic import BaseModel, Field


class Recommendation(str, enum.Enum):
    STRONG_PROCEED = "STRONG_PROCEED"
    PROCEED = "PROCEED"
    BORDERLINE = "BORDERLINE"
    DO_NOT_PROCEED = "DO_NOT_PROCEED"


class DimensionScore(BaseModel):
    score: float = Field(ge=0, le=10, description="Score 0-10 for this dimension.")
    confidence: float = Field(ge=0, le=1, description="Model confidence in the score.")
    summary: str = Field(description="Human-readable summary of performance.")
    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(
        default_factory=list,
        description="Transcript quotes backing the score. Empty when insufficient evidence.",
    )
    evidence_status: str = Field(
        default="SUFFICIENT", description="One of: SUFFICIENT, INSUFFICIENT, PARTIAL"
    )


class EvidenceItem(BaseModel):
    quote: str = Field(description="Quote from the candidate's transcript.")
    reason: str = Field(description="Why this quote supports the score.")


class AssessmentResult(BaseModel):
    overall_score: float = Field(ge=0, le=10)
    recommendation: Recommendation
    summary: str
    dimensions: dict[str, DimensionScore]
    key_strengths: list[str] = Field(default_factory=list)
    key_concerns: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    fairness_note: str | None = Field(
        default=None,
        description="Optional note that assessment focuses on tutoring behaviour, not identity.",
    )

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


DimensionScore.model_rebuild()
