from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_repository
from app.core.exceptions import AssessmentNotReadyError
from app.models.session import AssessmentStatus
from app.repositories.sessions import SessionRepository
from app.schemas.assessment import AssessmentResponse

router = APIRouter(tags=["Assessments"])


@router.get(
    "/sessions/{session_id}/assessment",
    response_model=AssessmentResponse,
    summary="Get session assessment",
    description="Returns the evidence-backed assessment for a completed session.",
)
async def get_assessment(
    session_id: str,
    repo: SessionRepository = Depends(get_repository),
) -> AssessmentResponse:
    session = await repo.get(session_id)
    if session.assessment_status != AssessmentStatus.COMPLETED:
        raise AssessmentNotReadyError()
    if session.assessment is None:
        raise AssessmentNotReadyError()
    return AssessmentResponse(session_id=session_id, assessment=session.assessment)
