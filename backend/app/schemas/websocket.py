from __future__ import annotations

import enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class ClientEventType(str, enum.Enum):
    SESSION_START = "session.start"
    AUDIO_CHUNK = "audio.chunk"
    AUDIO_END = "audio.end"
    CANDIDATE_TEXT = "candidate.text"  # testing shortcut: bypasses STT
    SESSION_END = "session.end"
    PING = "ping"


class ServerEventType(str, enum.Enum):
    SESSION_READY = "session.ready"
    INTERVIEWER_TRANSCRIPT = "interviewer.transcript"
    INTERVIEWER_STATE = "interviewer.state"
    CANDIDATE_TRANSCRIPT = "candidate.transcript"
    INTERVIEWER_RESPONSE = "interviewer.response"
    AUDIO_START = "audio.start"
    AUDIO_CHUNK = "audio.chunk"
    AUDIO_END = "audio.end"
    SILENCE_PROMPT = "silence.prompt"
    ASSESSMENT_STARTED = "assessment.started"
    ASSESSMENT_COMPLETED = "assessment.completed"
    SESSION_COMPLETED = "session.completed"
    ERROR = "error"
    PONG = "pong"


class ClientEvent(BaseModel):
    """A message sent by the client (text frame)."""

    type: ClientEventType
    data: Any | None = Field(default=None, description="Optional JSON payload for the event.")


class ServerEvent(BaseModel):
    """A message sent to the client (text frame)."""

    type: ServerEventType
    data: dict[str, Any] | None = Field(default=None)


def error_event(code: str, message: str) -> ServerEvent:
    return ServerEvent(type=ServerEventType.ERROR, data={"code": code, "message": message})


def audio_start_event(format: str, sample_rate: int) -> ServerEvent:
    return ServerEvent(
        type=ServerEventType.AUDIO_START,
        data={"format": format, "sample_rate": sample_rate},
    )


# -- Event payload builders -------------------------------------------------


def session_ready(session_id: str) -> ServerEvent:
    return ServerEvent(type=ServerEventType.SESSION_READY, data={"session_id": session_id})


def interviewer_transcript(text: str) -> ServerEvent:
    return ServerEvent(type=ServerEventType.INTERVIEWER_TRANSCRIPT, data={"text": text})


def interviewer_state(state: Literal["speaking", "listening", "thinking"]) -> ServerEvent:
    return ServerEvent(type=ServerEventType.INTERVIEWER_STATE, data={"state": state})


def candidate_transcript(text: str) -> ServerEvent:
    return ServerEvent(type=ServerEventType.CANDIDATE_TRANSCRIPT, data={"text": text})


def interviewer_response(text: str, stage: str) -> ServerEvent:
    return ServerEvent(type=ServerEventType.INTERVIEWER_RESPONSE, data={"text": text, "stage": stage})


def silence_prompt(message: str) -> ServerEvent:
    return ServerEvent(type=ServerEventType.SILENCE_PROMPT, data={"message": message})


def assessment_started() -> ServerEvent:
    return ServerEvent(type=ServerEventType.ASSESSMENT_STARTED)


def assessment_completed(session_id: str) -> ServerEvent:
    return ServerEvent(type=ServerEventType.ASSESSMENT_COMPLETED, data={"session_id": session_id})
