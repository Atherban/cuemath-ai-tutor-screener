from __future__ import annotations

import json


def _open(ws, event_type):
    msg = ws.receive()
    assert "text" in msg
    data = json.loads(msg["text"])
    assert data["type"] == event_type
    return data


def _drain_until_listening(ws, max_messages=30):
    """Consume messages until the interviewer returns to the listening state."""
    events = []
    for _ in range(max_messages):
        msg = ws.receive()
        if "text" in msg:
            data = json.loads(msg["text"])
            events.append(data)
            if (
                data["type"] == "interviewer.state"
                and (data.get("data") or {}).get("state") == "listening"
            ):
                return events
        # binary frames are audio chunks — keep going
    raise AssertionError(f"listening state not received; saw: {events}")


def test_websocket_successful_connection(client):
    sid = client.post("/api/v1/sessions").json()["session_id"]
    with client.websocket_connect(f"/ws/interview/{sid}") as ws:
        _open(ws, "session.ready")


def test_websocket_invalid_session(client):
    with client.websocket_connect("/ws/interview/does-not-exist") as ws:
        data = _open(ws, "error")
        assert data["data"]["code"] == "SESSION_NOT_FOUND"


def test_websocket_completed_session_rejected(client):
    sid = client.post("/api/v1/sessions").json()["session_id"]
    client.post(f"/api/v1/sessions/{sid}/complete")
    with client.websocket_connect(f"/ws/interview/{sid}") as ws:
        data = _open(ws, "error")
        assert data["data"]["code"] == "SESSION_ALREADY_COMPLETED"


def test_websocket_malformed_event(client):
    sid = client.post("/api/v1/sessions").json()["session_id"]
    with client.websocket_connect(f"/ws/interview/{sid}") as ws:
        _open(ws, "session.ready")
        ws.send_text("{not valid json")
        data = _open(ws, "error")
        assert data["data"]["code"] == "INVALID_MESSAGE"


def test_websocket_unknown_event_type(client):
    sid = client.post("/api/v1/sessions").json()["session_id"]
    with client.websocket_connect(f"/ws/interview/{sid}") as ws:
        _open(ws, "session.ready")
        ws.send_json({"type": "unknown.event"})
        data = _open(ws, "error")
        assert data["data"]["code"] == "INVALID_MESSAGE"


def test_websocket_start_and_opening(client):
    sid = client.post("/api/v1/sessions").json()["session_id"]
    with client.websocket_connect(f"/ws/interview/{sid}") as ws:
        _open(ws, "session.ready")
        ws.send_json({"type": "session.start"})
        events = _drain_until_listening(ws)
        types = {e["type"] for e in events}
        assert "interviewer.transcript" in types
        assert "interviewer.state" in types


def test_websocket_candidate_message(client, fake_stt, fake_ai):
    sid = client.post("/api/v1/sessions").json()["session_id"]
    fake_ai.enqueue("That's a thoughtful approach. Could you say more about checking understanding?")
    with client.websocket_connect(f"/ws/interview/{sid}") as ws:
        _open(ws, "session.ready")
        ws.send_json({"type": "session.start"})
        _drain_until_listening(ws)

        ws.send_bytes(b"\x00" * 4000)
        ws.send_json({"type": "audio.end"})

        got_candidate = False
        got_response = False
        for _ in range(40):
            msg = ws.receive()
            if "text" not in msg:
                continue
            data = json.loads(msg["text"])
            if data["type"] == "candidate.transcript":
                got_candidate = True
            if data["type"] == "interviewer.response":
                got_response = True
            if data["type"] == "audio.end":
                break
        assert got_candidate
        assert got_response


def test_websocket_audio_too_short(client):
    sid = client.post("/api/v1/sessions").json()["session_id"]
    with client.websocket_connect(f"/ws/interview/{sid}") as ws:
        _open(ws, "session.ready")
        ws.send_json({"type": "session.start"})
        _drain_until_listening(ws)
        ws.send_bytes(b"")
        ws.send_json({"type": "audio.end"})
        data = _open(ws, "error")
        assert data["data"]["code"] == "AUDIO_TOO_SHORT"


def test_websocket_full_interview_and_assessment(client, fake_ai):
    sid = client.post("/api/v1/sessions").json()["session_id"]
    evaluator_output = json.dumps(
        {
            "dimensions": {
                "clarity": {"score": 8, "confidence": 0.8, "summary": "c", "evidence": [
                    {"quote": "I explain step by step.", "reason": "structured"}]},
                "simplicity": {"score": 8, "confidence": 0.8, "summary": "s", "evidence": [
                    {"quote": "I explain step by step.", "reason": "simple"}]},
                "patience": {"score": 8, "confidence": 0.8, "summary": "p", "evidence": [
                    {"quote": "I explain step by step.", "reason": "patient"}]},
                "warmth": {"score": 8, "confidence": 0.8, "summary": "w", "evidence": [
                    {"quote": "I explain step by step.", "reason": "warm"}]},
                "fluency": {"score": 8, "confidence": 0.8, "summary": "f", "evidence": [
                    {"quote": "I explain step by step.", "reason": "fluent"}]},
                "adaptability": {"score": 8, "confidence": 0.8, "summary": "a", "evidence": [
                    {"quote": "I explain step by step.", "reason": "adaptive"}]},
            },
            "key_strengths": ["Structured"],
            "key_concerns": [],
            "overall_score": 8.0,
            "confidence": 0.8,
            "summary": "Good.",
        }
    )
    fake_ai.enqueue(evaluator_output)

    with client.websocket_connect(f"/ws/interview/{sid}") as ws:
        _open(ws, "session.ready")
        ws.send_json({"type": "session.start"})
        _drain_until_listening(ws)

        # Push the interview through the stages with substantive answers.
        answers = [
            "I love working with kids and have tutored my younger brother.",
            "I'd split a pizza into two equal parts and show one half.",
            "I'd draw it on paper and count the pieces with them.",
            "I'd say everyone can learn math with practice.",
            "If it still doesn't work, I'd try their favourite example.",
        ]
        assessment_events = []
        for _answer in answers:
            ws.send_bytes(b"\x00" * 4000)
            ws.send_json({"type": "audio.end"})
            # Drain until interviewer returns to listening.
            for _ in range(50):
                msg = ws.receive()
                if "text" not in msg:
                    continue
                data = json.loads(msg["text"])
                if data["type"] == "audio.end":
                    break

        # End the interview and observe the assessment flow.
        ws.send_json({"type": "session.end"})
        saw_assessment_started = False
        saw_assessment_completed = False
        saw_completed = False
        for _ in range(60):
            msg = ws.receive()
            if "text" not in msg:
                continue
            data = json.loads(msg["text"])
            assessment_events.append(data["type"])
            if data["type"] == "assessment.started":
                saw_assessment_started = True
            if data["type"] == "session.completed":
                saw_completed = True
            if data["type"] == "assessment.completed":
                saw_assessment_completed = True
                break
        assert saw_assessment_started
        assert saw_completed
        assert saw_assessment_completed

    # Assessment is retrievable over HTTP.
    resp = client.get(f"/api/v1/sessions/{sid}/assessment")
    assert resp.status_code == 200
    assert resp.json()["assessment"]["recommendation"] in {
        "STRONG_PROCEED", "PROCEED", "BORDERLINE", "DO_NOT_PROCEED"
    }


def test_websocket_candidate_text_mode(client, fake_ai):
    """Text-mode path bypasses STT and drives the engine with typed answers."""
    sid = client.post("/api/v1/sessions").json()["session_id"]
    fake_ai.enqueue("That's a great way to explain it.")
    with client.websocket_connect(f"/ws/interview/{sid}") as ws:
        _open(ws, "session.ready")
        ws.send_json({"type": "session.start"})
        _drain_until_listening(ws)

        ws.send_json({"type": "candidate.text", "data": {"text": "I'd split a pizza into two halves."}})

        got_candidate = False
        got_response = False
        for _ in range(40):
            msg = ws.receive()
            if "text" not in msg:
                continue
            data = json.loads(msg["text"])
            if data["type"] == "candidate.transcript":
                assert "pizza" in data["data"]["text"]
                got_candidate = True
            if data["type"] == "interviewer.response":
                got_response = True
            if data["type"] == "audio.end":
                break
        assert got_candidate
        assert got_response


def test_websocket_candidate_text_missing_field(client):
    sid = client.post("/api/v1/sessions").json()["session_id"]
    with client.websocket_connect(f"/ws/interview/{sid}") as ws:
        _open(ws, "session.ready")
        ws.send_json({"type": "candidate.text", "data": {}})
        data = _open(ws, "error")
        assert data["data"]["code"] == "INVALID_MESSAGE"


def test_websocket_disconnect_persists_session(client):
    sid = client.post("/api/v1/sessions").json()["session_id"]
    with client.websocket_connect(f"/ws/interview/{sid}") as ws:
        _open(ws, "session.ready")
        ws.send_json({"type": "session.start"})
        _drain_until_listening(ws)
    # After context exit the socket is closed; session still retrievable.
    resp = client.get(f"/api/v1/sessions/{sid}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "IN_PROGRESS"
