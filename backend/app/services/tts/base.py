from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class AudioResult:
    audio: bytes
    format: str  # e.g. "audio/mpeg", "audio/wav"
    sample_rate: int | None = None


@runtime_checkable
class TextToSpeech(Protocol):
    """Abstraction over text-to-speech backends.

    Implementations must be async and must not block the event loop.
    """

    async def synthesize(self, text: str) -> AudioResult: ...
