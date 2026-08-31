from __future__ import annotations

import asyncio
import io
import logging
import wave

import numpy as np

from app.core.config import Settings
from app.core.exceptions import TtsFailedError
from app.services.tts.base import AudioResult, TextToSpeech

logger = logging.getLogger(__name__)

# Minimum amplitude threshold; anything below is treated as silence.
_SILENCE_THRESHOLD = 150
# Extra audio to keep after the last detected speech (avoids an abrupt cut).
_KEEP_TAIL_SEC = 0.3


class EdgeTTS:
    """Text-to-speech using Microsoft Edge TTS (free, high-quality voice).

    Edge TTS returns MP3 audio. The MP3 is decoded to 16-bit PCM and trailing
    silence is trimmed so the client never receives a 20-second file for a
    5-second utterance (edge-tts appends several seconds of trailing silence).
    """

    name = "edge"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def synthesize(self, text: str) -> AudioResult:
        if not text.strip():
            raise TtsFailedError("Cannot synthesize empty text.")
        try:
            import edge_tts
        except ImportError as exc:  # pragma: no cover
            raise TtsFailedError("The 'edge-tts' package is not installed.") from exc

        try:
            communicate = edge_tts.Communicate(
                text,
                voice=self._settings.tts_voice,
                rate=self._settings.tts_rate,
            )
            mp3_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    mp3_data += chunk["data"]
            if not mp3_data:
                raise TtsFailedError("Edge TTS returned no audio data.")

            # Decode MP3 -> 16-bit PCM mono, trim trailing silence.
            pcm = _decode_and_trim(mp3_data)
            # Wrap in WAV so the frontend's decodeAudioData works in all browsers.
            wav = _encode_wav(pcm, 24000)
            return AudioResult(audio=wav, format="audio/wav", sample_rate=24000)
        except TtsFailedError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("Edge TTS synthesis failed: %s", exc)
            raise TtsFailedError() from exc


def _decode_and_trim(mp3_bytes: bytes, target_sr: int = 24000) -> bytes:
    """Decode MP3 to 16-bit PCM mono, resample, and trim trailing silence."""
    import miniaudio
    import numpy as np

    snd = miniaudio.decode(mp3_bytes, output_format=miniaudio.SampleFormat.SIGNED16)
    arr = np.frombuffer(snd.samples, dtype=np.int16)

    # Convert to mono if stereo (average channels).
    if snd.nchannels == 2:
        arr = ((arr[0::2].astype(np.int32) + arr[1::2].astype(np.int32)) // 2).astype(np.int16)

    # Resample to the target rate if needed.
    if snd.sample_rate != target_sr:
        arr = _resample(arr, snd.sample_rate, target_sr)

    # Trim trailing silence (edge-tts appends a long silence tail).
    arr = _trim_trailing(arr, target_sr)

    return arr.tobytes()


def _trim_trailing(arr: np.ndarray, sr: int) -> np.ndarray:
    """Remove silence from the END of the audio only."""
    if len(arr) == 0:
        return arr
    non_silent = np.where(np.abs(arr) > _SILENCE_THRESHOLD)[0]
    if len(non_silent) == 0:
        return arr  # all silence — leave unchanged
    last_audio = non_silent[-1]
    keep_until = min(int(last_audio + sr * _KEEP_TAIL_SEC) + 1, len(arr))
    return arr[:keep_until]


def _resample(arr: np.ndarray, src_sr: int, dst_sr: int) -> np.ndarray:
    """Simple linear resample — adequate for speech."""
    import numpy as np

    if src_sr == dst_sr:
        return arr
    new_len = int(len(arr) * (dst_sr / src_sr))
    indices = np.linspace(0, len(arr) - 1, new_len)
    return np.interp(indices, np.arange(len(arr)), arr.astype(np.float32)).astype(np.int16)


def _encode_wav(pcm: bytes, sample_rate: int) -> bytes:
    """Wrap raw 16-bit PCM mono samples in a WAV container.

    `decodeAudioData` in browsers handles WAV natively; it cannot decode raw
    PCM. The 44-byte RIFF header is negligible.
    """
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    return buf.getvalue()


class MockTTS:
    """Deterministic local TTS provider for development and tests.

    Returns minimal valid audio so the pipeline can be exercised without
    network access.
    """

    name = "mock"

    async def synthesize(self, text: str) -> AudioResult:
        await asyncio.sleep(0.01)
        wav = _make_silent_wav()
        return AudioResult(audio=wav, format="audio/wav", sample_rate=16000)


def _make_silent_wav(duration_sec: float = 0.2, sample_rate: int = 16000) -> bytes:
    """Generate a silent WAV file of the given duration."""
    num_samples = int(duration_sec * sample_rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * num_samples)
    return buf.getvalue()


def build_tts(settings: Settings) -> TextToSpeech:
    provider = settings.tts_provider.lower()
    if provider == "edge":
        return EdgeTTS(settings)
    if provider == "mock":
        return MockTTS()
    raise TtsFailedError(f"Unknown TTS provider: {settings.tts_provider}")
