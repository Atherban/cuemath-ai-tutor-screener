from __future__ import annotations

from pydantic import BaseModel

from app.models.assessment import AssessmentResult


class AssessmentResponse(BaseModel):
    session_id: str
    assessment: AssessmentResult
