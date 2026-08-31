from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base class for all application-specific errors.

    `code` is a stable machine-readable identifier that is safe to expose to
    clients (e.g. "SESSION_NOT_FOUND"). `status_code` maps to the HTTP status
    for REST endpoints. No internal exception details ever reach the client.
    """

    code: str = "INTERNAL_ERROR"
    status_code: int = 500
    message: str = "An unexpected error occurred."
    details: dict[str, Any] | None = None

    def __init__(self, message: str | None = None, *, details: dict[str, Any] | None = None) -> None:
        self.message = message or self.message
        self.details = details
        super().__init__(self.message)


class SessionNotFoundError(AppError):
    code = "SESSION_NOT_FOUND"
    status_code = 404
    message = "Session not found."


class SessionAlreadyCompletedError(AppError):
    code = "SESSION_ALREADY_COMPLETED"
    status_code = 409
    message = "Session is already completed."


class SessionInProgressError(AppError):
    code = "SESSION_IN_PROGRESS"
    status_code = 409
    message = "Session is already in progress."


class SessionNotReadyError(AppError):
    code = "SESSION_NOT_READY"
    status_code = 409
    message = "Session is not ready for this operation."


class InvalidMessageError(AppError):
    code = "INVALID_MESSAGE"
    status_code = 400
    message = "Malformed or unsupported message."


class TranscriptionFailedError(AppError):
    code = "TRANSCRIPTION_FAILED"
    status_code = 500
    message = "We couldn't understand that response. Please try again."


class AudioTooShortError(AppError):
    code = "AUDIO_TOO_SHORT"
    status_code = 400
    message = "The audio was too short to understand. Please try again."


class TtsFailedError(AppError):
    code = "TTS_FAILED"
    status_code = 500
    message = "Speech synthesis failed."


class AIProviderError(AppError):
    code = "AI_PROVIDER_FAILED"
    status_code = 500
    message = "The AI service is temporarily unavailable."


class AssessmentError(AppError):
    code = "ASSESSMENT_FAILED"
    status_code = 500
    message = "Assessment could not be generated."


class AssessmentNotReadyError(AppError):
    code = "ASSESSMENT_NOT_READY"
    status_code = 409
    message = "Assessment is not available yet."
