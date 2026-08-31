from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.session import AssessmentStatus, SessionStatus


class SessionCreateRequest(BaseModel):
    candidate_id: str | None = Field(
        default="anonymous",
        max_length=128,
        description="Optional anonymous candidate identifier.",
    )


class TranscriptEntryResponse(BaseModel):
    role: str
    text: str
    stage: str | None = None
    timestamp: datetime


class SessionResponse(BaseModel):
    session_id: str
    candidate_id: str
    status: SessionStatus
    started_at: datetime | None = None
    ended_at: datetime | None = None
    current_stage: str | None = None
    turn_count: int
    short_answer_count: int
    long_answer_count: int
    topics_covered: list[str]
    assessment_status: AssessmentStatus
    fail_reason: str | None = None


class SessionDetailResponse(SessionResponse):
    conversation_history: list[TranscriptEntryResponse]


class SessionCompleteResponse(BaseModel):
    session_id: str
    status: SessionStatus
    message: str
