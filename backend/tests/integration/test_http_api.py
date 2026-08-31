from __future__ import annotations

from app.models.assessment import AssessmentResult, DimensionScore, Recommendation
from app.models.session import AssessmentStatus, InterviewSession, SessionStatus


def test_health(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_create_session(client):
    resp = client.post("/api/v1/sessions", json={"candidate_id": "candidate-123"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"]
    assert body["candidate_id"] == "candidate-123"
    assert body["status"] == "CREATED"
    assert body["assessment_status"] == "PENDING"
    assert body["turn_count"] == 0


def test_get_session(client):
    sid = client.post("/api/v1/sessions").json()["session_id"]
    resp = client.get(f"/api/v1/sessions/{sid}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == sid
    assert "conversation_history" in body


def test_get_invalid_session(client):
    resp = client.get("/api/v1/sessions/nope")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "SESSION_NOT_FOUND"


def test_complete_session(client):
    sid = client.post("/api/v1/sessions").json()["session_id"]
    resp = client.post(f"/api/v1/sessions/{sid}/complete")
    assert resp.status_code == 200
    assert resp.json()["status"] == "COMPLETED"


def test_complete_session_twice_conflict(client):
    sid = client.post("/api/v1/sessions").json()["session_id"]
    client.post(f"/api/v1/sessions/{sid}/complete")
    resp = client.post(f"/api/v1/sessions/{sid}/complete")
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "SESSION_ALREADY_COMPLETED"


def test_assessment_not_ready(client):
    sid = client.post("/api/v1/sessions").json()["session_id"]
    resp = client.get(f"/api/v1/sessions/{sid}/assessment")
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "ASSESSMENT_NOT_READY"


async def test_assessment_retrieval(client, app):
    from app.api.deps import init_repository

    repo = init_repository()
    session = InterviewSession()
    session.status = SessionStatus.COMPLETED
    session.assessment_status = AssessmentStatus.COMPLETED
    session.assessment = AssessmentResult(
        overall_score=8.2,
        recommendation=Recommendation.PROCEED,
        summary="Good candidate.",
        dimensions={
            "clarity": DimensionScore(score=8, confidence=0.9, summary="Clear."),
            "simplicity": DimensionScore(score=8, confidence=0.9, summary="Clear."),
            "patience": DimensionScore(score=8, confidence=0.9, summary="Clear."),
            "warmth": DimensionScore(score=8, confidence=0.9, summary="Clear."),
            "fluency": DimensionScore(score=8, confidence=0.9, summary="Clear."),
        },
        confidence=0.9,
    )
    await repo.create(session)

    resp = client.get(f"/api/v1/sessions/{session.session_id}/assessment")
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == session.session_id
    assert body["assessment"]["recommendation"] == "PROCEED"
    assert body["assessment"]["overall_score"] == 8.2
    assert set(body["assessment"]["dimensions"].keys()) == {
        "clarity", "simplicity", "patience", "warmth", "fluency"
    }
