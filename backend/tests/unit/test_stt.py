from __future__ import annotations

import io

import pytest

from app.core.exceptions import TranscriptionFailedError
from app.services.stt.local import LocalSTT


class _FakeSegment:
    def __init__(self, text: str, avg_logprob: float = -0.3) -> None:
        self.text = text
        self.avg_logprob = avg_logprob


class _FakeInfo:
    language = "en"


class _FakeModel:
    """Records the audio argument passed to transcribe."""

    def __init__(self) -> None:
        self.received_audio = None
        self.received_kwargs = None

    def transcribe(self, audio, **kwargs):
        self.received_audio = audio
        self.received_kwargs = kwargs
        return iter([_FakeSegment("I would explain one half")]), _FakeInfo()


@pytest.fixture
def settings():
    from app.core.config import Settings

    return Settings(
        stt_provider="local",
        stt_model="tiny",
        stt_language="en",
        stt_device="cpu",
        stt_compute_type="int8",
    )


async def test_transcribe_accepts_raw_bytes(monkeypatch, settings):
    """Raw bytes (as sent by the browser over WebSocket) must be accepted."""
    fake_model = _FakeModel()
    stt = LocalSTT(settings)
    monkeypatch.setattr(stt, "_get_model", _async(fake_model))

    result = await stt.transcribe(b"RIFF....WAVE fake wav bytes")

    assert result.text == "I would explain one half"
    assert result.language == "en"
    assert result.confidence is not None
    # faster-whisper must receive a file-like object, never raw bytes.
    assert hasattr(fake_model.received_audio, "read")
    assert isinstance(fake_model.received_audio, io.BytesIO)
    assert fake_model.received_kwargs["language"] == "en"


async def test_transcribe_empty_raises(monkeypatch, settings):
    stt = LocalSTT(settings)
    with pytest.raises(TranscriptionFailedError):
        await stt.transcribe(b"")


async def test_transcribe_no_speech_raises(monkeypatch, settings):
    """Empty transcription (e.g. pure silence) is treated as a failure."""

    class _EmptyModel(_FakeModel):
        def transcribe(self, audio, **kwargs):
            self.received_audio = audio
            return iter([]), _FakeInfo()

    fake_model = _EmptyModel()
    stt = LocalSTT(settings)
    monkeypatch.setattr(stt, "_get_model", _async(fake_model))

    with pytest.raises(TranscriptionFailedError):
        await stt.transcribe(b"RIFF....WAVE silence")


def _async(value):
    async def _get():
        return value

    return _get
