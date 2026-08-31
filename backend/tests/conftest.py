from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure the `app` package is importable regardless of CWD.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.ai.base import AIResponse, ChatMessage  # noqa: E402


class FakeAIProvider:
    """Deterministic AI provider for tests."""

    name = "fake"

    def __init__(self, responses: list[str] | None = None) -> None:
        self._responses = list(responses or [])
        self.calls: list[list[ChatMessage]] = []

    def enqueue(self, text: str) -> None:
        self._responses.append(text)

    async def generate_response(
        self, messages: list[ChatMessage], *, temperature: float = 0.7, max_tokens: int | None = None
    ) -> AIResponse:
        self.calls.append(messages)
        return AIResponse(text=self._next())

    async def generate_text(
        self, prompt: str, *, temperature: float = 0.7, max_tokens: int | None = None
    ) -> str:
        self.calls.append([ChatMessage(role="user", content=prompt)])
        return self._next()

    def _next(self) -> str:
        return self._responses.pop(0) if self._responses else "That's a good point."


class FakeSTT:
    """Deterministic STT provider for tests."""

    def __init__(self, text: str = "I would explain fractions using a pizza.") -> None:
        self.text = text
        self.transcriptions: list[bytes] = []

    async def transcribe(self, audio: bytes):
        from app.services.stt.base import TranscriptionResult

        self.transcriptions.append(audio)
        return TranscriptionResult(text=self.text, language="en", confidence=0.9)


class FakeTTS:
    """Deterministic TTS provider for tests."""

    def __init__(self) -> None:
        self.synthesized: list[str] = []

    async def synthesize(self, text: str):
        from app.services.tts.base import AudioResult

        self.synthesized.append(text)
        # 100ms of 16-bit mono PCM at 24000Hz
        pcm = b"\x00\x00" * 2400
        return AudioResult(audio=pcm, format="audio/pcm_s16le", sample_rate=24000)


@pytest.fixture
def fake_ai():
    return FakeAIProvider()


@pytest.fixture
def fake_stt():
    return FakeSTT()


@pytest.fixture
def fake_tts():
    return FakeTTS()


@pytest.fixture
def settings():
    from app.core.config import Settings

    return Settings(
        ai_provider="mock",
        stt_provider="mock",
        tts_provider="mock",
        stt_min_audio_bytes=1,
        max_silence_seconds=60,
        silence_prompt_seconds=30,
    )


@pytest.fixture
def engine(fake_ai, settings):
    from app.services.interview.engine import InterviewEngine

    return InterviewEngine(settings, fake_ai)


@pytest.fixture
def session():
    from app.models.session import InterviewSession

    return InterviewSession()


@pytest.fixture
def repository():
    from app.repositories.sessions import SessionRepository

    return SessionRepository()


@pytest.fixture
def app(monkeypatch, fake_ai, fake_stt, fake_tts):
    import app.api.deps as deps
    import app.main as main

    def reset_repo():
        deps.init_repository()

    monkeypatch.setattr(main, "build_provider", lambda s: fake_ai)
    monkeypatch.setattr(main, "build_stt", lambda s: fake_stt)
    monkeypatch.setattr(main, "build_tts", lambda s: fake_tts)
    application = main.create_app()
    return application


@pytest.fixture
def client(app):
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c
