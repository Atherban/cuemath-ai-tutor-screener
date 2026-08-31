from __future__ import annotations

import pytest

from app.core.exceptions import SessionNotFoundError
from app.models.session import InterviewSession


async def test_create_and_get(repository):
    session = InterviewSession(candidate_id="cand-1")
    await repository.create(session)

    fetched = await repository.get(session.session_id)
    assert fetched.session_id == session.session_id
    assert fetched.candidate_id == "cand-1"


async def test_get_missing_raises(repository):
    with pytest.raises(SessionNotFoundError):
        await repository.get("nope")


async def test_update(repository):
    session = InterviewSession()
    await repository.create(session)
    session.turn_count = 3
    await repository.update(session)

    fetched = await repository.get(session.session_id)
    assert fetched.turn_count == 3


async def test_update_missing_raises(repository):
    session = InterviewSession()
    with pytest.raises(SessionNotFoundError):
        await repository.update(session)


async def test_save_assessment(repository):
    session = InterviewSession()
    await repository.create(session)
    from app.models.session import AssessmentStatus

    await repository.save_assessment(session.session_id, AssessmentStatus.COMPLETED)
    assert (await repository.get(session.session_id)).assessment_status == AssessmentStatus.COMPLETED
