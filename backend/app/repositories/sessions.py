from __future__ import annotations

from app.core.exceptions import SessionAlreadyCompletedError, SessionNotFoundError
from app.models.session import AssessmentStatus, InterviewSession, SessionStatus


class SessionRepository:
    """In-memory session store.

    This is the MVP persistence layer. It is intentionally isolated behind this
    class so a PostgreSQL/Redis backend can be swapped in without touching the
    rest of the application.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, InterviewSession] = {}

    async def create(self, session: InterviewSession) -> InterviewSession:
        self._sessions[session.session_id] = session
        return session

    async def get(self, session_id: str) -> InterviewSession:
        try:
            return self._sessions[session_id]
        except KeyError:
            raise SessionNotFoundError() from None

    async def update(self, session: InterviewSession) -> InterviewSession:
        if session.session_id not in self._sessions:
            raise SessionNotFoundError()
        self._sessions[session.session_id] = session
        return session

    async def save_assessment(
        self, session_id: str, assessment_status: AssessmentStatus
    ) -> InterviewSession:
        session = await self.get(session_id)
        session.assessment_status = assessment_status
        return session

    async def complete(self, session_id: str) -> InterviewSession:
        session = await self.get(session_id)
        if session.status == SessionStatus.COMPLETED:
            raise SessionAlreadyCompletedError()
        return session
