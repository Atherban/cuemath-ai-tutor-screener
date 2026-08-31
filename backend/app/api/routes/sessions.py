from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from app.api.deps import get_repository
from app.core.exceptions import SessionAlreadyCompletedError
from app.models.session import InterviewSession, SessionStatus
from app.repositories.sessions import SessionRepository
from app.schemas.session import (
    SessionCompleteResponse,
    SessionCreateRequest,
    SessionDetailResponse,
    SessionResponse,
    TranscriptEntryResponse,
)

router = APIRouter(tags=["Sessions"])


@router.post(
    "/sessions",
    response_model=SessionResponse,
    summary="Create an interview session",
    description="Creates a new anonymous interview session and returns its id.",
)
async def create_session(
    body: SessionCreateRequest | None = None,
    repo: SessionRepository = Depends(get_repository),
) -> SessionResponse:
    session = InterviewSession(
        candidate_id=(body.candidate_id if body and body.candidate_id else "anonymous")
    )
    await repo.create(session)
    return _to_response(session)


@router.get(
    "/sessions/{session_id}",
    response_model=SessionDetailResponse,
    summary="Get session details",
    description="Returns session state and full conversation transcript.",
)
async def get_session(
    session_id: str,
    repo: SessionRepository = Depends(get_repository),
) -> SessionDetailResponse:
    session = await repo.get(session_id)
    return _to_detail_response(session)


@router.post(
    "/sessions/{session_id}/complete",
    response_model=SessionCompleteResponse,
    summary="Mark a session complete",
    description="Marks a session as completed. Used by callers not going through the WebSocket flow.",
)
async def complete_session(
    session_id: str,
    repo: SessionRepository = Depends(get_repository),
) -> SessionCompleteResponse:
    session = await repo.complete(session_id)
    if session.status == SessionStatus.COMPLETED:
        raise SessionAlreadyCompletedError()
    session.status = SessionStatus.COMPLETED
    session.ended_at = session.ended_at or datetime.now(UTC)
    await repo.update(session)
    return SessionCompleteResponse(
        session_id=session_id,
        status=session.status,
        message="Session completed.",
    )


def _to_response(session: InterviewSession) -> SessionResponse:
    return SessionResponse(
        session_id=session.session_id,
        candidate_id=session.candidate_id,
        status=session.status,
        started_at=session.started_at,
        ended_at=session.ended_at,
        current_stage=session.current_stage,
        turn_count=session.turn_count,
        short_answer_count=session.short_answer_count,
        long_answer_count=session.long_answer_count,
        topics_covered=session.topics_covered,
        assessment_status=session.assessment_status,
        fail_reason=session.fail_reason,
    )


def _to_detail_response(session: InterviewSession) -> SessionDetailResponse:
    base = _to_response(session)
    history = [
        TranscriptEntryResponse(
            role=entry.role,
            text=entry.text,
            stage=entry.stage,
            timestamp=entry.timestamp,
        )
        for entry in session.conversation_history
    ]
    return SessionDetailResponse(**base.model_dump(), conversation_history=history)
