from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.models.assessment import AssessmentResult


class SessionStatus(str, enum.Enum):
    CREATED = "CREATED"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AssessmentStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class TranscriptEntry:
    role: str  # "interviewer" | "candidate"
    text: str
    stage: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class InterviewSession:
    """In-memory domain model for an interview session.

    This is the single source of truth for interview state and is persisted
    behind the `SessionRepository` abstraction.
    """

    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    candidate_id: str = "anonymous"
    status: SessionStatus = SessionStatus.CREATED
    started_at: datetime | None = None
    ended_at: datetime | None = None
    current_stage: str | None = None
    current_question: str | None = None
    conversation_history: list[TranscriptEntry] = field(default_factory=list)
    turn_count: int = 0
    silence_count: int = 0
    short_answer_count: int = 0
    long_answer_count: int = 0
    topics_covered: list[str] = field(default_factory=list)
    assessment_status: AssessmentStatus = AssessmentStatus.PENDING
    assessment: AssessmentResult | None = None
    error_code: str | None = None
    fail_reason: str | None = None
