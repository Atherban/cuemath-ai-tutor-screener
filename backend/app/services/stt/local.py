from __future__ import annotations

import asyncio
import io
import logging
from typing import Any

from app.core.config import Settings
from app.core.exceptions import TranscriptionFailedError
from app.services.stt.base import SpeechToText, TranscriptionResult

logger = logging.getLogger(__name__)


class LocalSTT:
    """Speech-to-text using faster-whisper (offline, free, MIT licensed).

    The model is loaded lazily on first use and transcription runs in a worker
    thread so the event loop stays responsive.
    """

    name = "local"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model: Any | None = None
        self._model_lock = asyncio.Lock()

    async def _get_model(self) -> Any:
        if self._model is None:
            async with self._model_lock:
                if self._model is None:
                    try:
                        from faster_whisper import WhisperModel
                    except ImportError as exc:  # pragma: no cover
                        raise TranscriptionFailedError(
                            "The 'faster-whisper' package is not installed."
                        ) from exc
                    logger.info(
                        "Loading faster-whisper model '%s' on %s",
                        self._settings.stt_model,
                        self._settings.stt_device,
                    )
                    self._model = await asyncio.to_thread(
                        WhisperModel,
                        self._settings.stt_model,
                        device=self._settings.stt_device,
                        compute_type=self._settings.stt_compute_type,
                    )
        return self._model

    async def transcribe(self, audio: bytes) -> TranscriptionResult:
        if not audio:
            raise TranscriptionFailedError()
        try:
            model = await self._get_model()
            # faster-whisper expects a file path, file-like object, or numpy
            # array — never raw bytes. Wrap them in BytesIO so the WAV can be
            # decoded (handles 16/24/32-bit PCM, any sample rate).
            audio_stream = io.BytesIO(audio)
            segments, info = await asyncio.to_thread(
                model.transcribe,
                audio_stream,
                language=self._settings.stt_language,
                beam_size=1,
                vad_filter=True,
            )
            segment_list = list(await asyncio.to_thread(_consume, segments))
            text = " ".join(s.text.strip() for s in segment_list).strip()
            if not text:
                raise TranscriptionFailedError()
            return TranscriptionResult(
                text=text,
                language=getattr(info, "language", None),
                confidence=_average_confidence(segment_list),
            )
        except TranscriptionFailedError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("Local STT failed: %s", exc)
            raise TranscriptionFailedError() from exc


def _consume(segments: Any) -> list[Any]:
    return list(segments)


def _average_confidence(segments: list[Any]) -> float | None:
    scores = [getattr(s, "avg_logprob", None) for s in segments]
    scores = [s for s in scores if s is not None]
    if not scores:
        return None
    return max(0.0, min(1.0, sum(scores) / len(scores) + 1.0))


def build_stt(settings: Settings) -> SpeechToText:
    provider = settings.stt_provider.lower()
    if provider == "local":
        return LocalSTT(settings)
    raise TranscriptionFailedError(f"Unknown STT provider: {settings.stt_provider}")
