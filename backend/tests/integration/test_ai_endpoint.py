from __future__ import annotations


def test_ai_test_endpoint_with_provider(client, fake_ai):
    fake_ai.enqueue("Hello! I'm your friendly tutor interviewer.")
    resp = client.post("/api/v1/ai/test", json={"prompt": "Say hello"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "fake"
    assert body["response"] == "Hello! I'm your friendly tutor interviewer."


def test_ai_test_endpoint_default_prompt(client, fake_ai):
    fake_ai.enqueue("Hello future tutor!")
    resp = client.post("/api/v1/ai/test")
    assert resp.status_code == 200
