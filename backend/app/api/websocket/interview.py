from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime

from fastapi import WebSocket, WebSocketDisconnect

from app.core.config import Settings
from app.core.exceptions import (
    AppError,
    InvalidMessageError,
    SessionNotFoundError,
    TranscriptionFailedError,
    TtsFailedError,
)
from app.models.session import (
    AssessmentStatus,
    InterviewSession,
    SessionStatus,
)
from app.repositories.sessions import SessionRepository
from app.schemas.websocket import (
    ClientEvent,
    ClientEventType,
    ServerEvent,
    ServerEventType,
    assessment_completed,
    assessment_started,
    audio_start_event,
    candidate_transcript,
    error_event,
    interviewer_response,
    interviewer_state,
    interviewer_transcript,
    session_ready,
    silence_prompt,
)
from app.services.assessment.evaluator import AssessmentEvaluator
from app.services.interview.engine import InterviewEngine
from app.services.interview.prompts import (
    SILENCE_GENTLE,
    SILENCE_OFFER_CHANCE,
)
from app.services.stt.base import SpeechToText
from app.services.tts.base import AudioResult, TextToSpeech

logger = logging.getLogger(__name__)

AUDIO_CHUNK_SIZE = 8192

_WS_FRIENDLY_MESSAGES = {
    "AI_PROVIDER_FAILED": "I'm having trouble responding right now. Could you say that again?",
    "TTS_FAILED": "I couldn't play that message. Let's continue.",
    "TRANSCRIPTION_FAILED": "We couldn't understand that response. Please try again.",
    "AUDIO_TOO_SHORT": "The audio was too short to understand. Please try again.",
    "INTERNAL_ERROR": "Something went wrong. Please try again.",
}


def _friendly_message(code: str) -> str:
    return _WS_FRIENDLY_MESSAGES.get(code, "Something went wrong. Please try again.")


class _ActivityClock:
    """Tracks seconds since the last client activity."""

    def __init__(self) -> None:
        self._last = datetime.now(UTC)
        self.silence_prompt_sent = False
        self.offer_sent = False

    def touch(self) -> None:
        self._last = datetime.now(UTC)
        self.silence_prompt_sent = False
        self.offer_sent = False

    def idle_seconds(self) -> float:
        return (datetime.now(UTC) - self._last).total_seconds()


class InterviewWebSocketController:
    """Thin WebSocket lifecycle controller.

    Handles connection lifecycle, protocol framing, and audio buffering. All
    interview business logic lives in `InterviewEngine` and the providers.
    """

    def __init__(
        self,
        repository: SessionRepository,
        engine: InterviewEngine,
        stt: SpeechToText,
        tts: TextToSpeech,
        evaluator: AssessmentEvaluator,
        settings: Settings,
    ) -> None:
        self._repo = repository
        self._engine = engine
        self._stt = stt
        self._tts = tts
        self._evaluator = evaluator
        self._settings = settings
        self._active: set[str] = set()
        # Sessions whose interviewer is currently in the "listening" state.
        # The silence monitor only prompts while the interviewer is waiting
        # for input, never while it is "thinking" (STT/AI/TTS in progress).
        self._listening: set[str] = set()

    async def handle(self, websocket: WebSocket, session_id: str) -> None:
        """Accept and run the interview for a single WebSocket connection."""
        try:
            session = await self._repo.get(session_id)
        except SessionNotFoundError:
            await self._reject(websocket, "SESSION_NOT_FOUND", "Session not found.")
            return

        if session.session_id in self._active:
            await self._reject(websocket, "SESSION_ALREADY_CONNECTED", "This session is already connected.")
            return
        if session.status == SessionStatus.COMPLETED:
            await self._reject(websocket, "SESSION_ALREADY_COMPLETED", "This session has already been completed.")
            return

        await websocket.accept()
        self._active.add(session_id)
        logger.info("WebSocket connected", extra={"session_id": session_id})

        clock = _ActivityClock()
        silence_task = asyncio.create_task(self._silence_monitor(websocket, session, clock))

        try:
            if session.status == SessionStatus.CREATED:
                session.status = SessionStatus.READY
                await self._repo.update(session)
            await self._send(websocket, session_ready(session_id))

            audio_buffer = bytearray()
            await self._run_event_loop(websocket, session, clock, audio_buffer)
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected", extra={"session_id": session_id})
        except AppError:
            # Safety net: never let a provider error kill the connection.
            await self._send(
                websocket,
                error_event("INTERNAL_ERROR", "Something went wrong. Please try again."),
            )
        except asyncio.CancelledError:
            logger.info("WebSocket handler cancelled", extra={"session_id": session_id})
            raise
        except Exception:  # noqa: BLE001 - last-resort guard; never leak traces.
            logger.exception("Unexpected WebSocket handler error", extra={"session_id": session_id})
        finally:
            silence_task.cancel()
            self._active.discard(session_id)
            self._listening.discard(session_id)
            try:
                await self._repo.update(session)
            except Exception:  # noqa: BLE001
                logger.warning("Failed to persist session on disconnect", extra={"session_id": session_id})
            logger.info("WebSocket cleaned up", extra={"session_id": session_id})

    # -- Event loop ---------------------------------------------------------

    async def _run_event_loop(
        self,
        websocket: WebSocket,
        session: InterviewSession,
        clock: _ActivityClock,
        audio_buffer: bytearray,
    ) -> None:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                return
            if "bytes" in message:
                audio_buffer.extend(message["bytes"])
                clock.touch()
                continue
            if "text" in message:
                try:
                    event = self._parse_event(message["text"])
                except InvalidMessageError:
                    await self._send(
                        websocket,
                        error_event("INVALID_MESSAGE", "Malformed or unsupported message."),
                    )
                    continue
                clock.touch()
                try:
                    done = await self._dispatch(websocket, session, event, audio_buffer)
                except AppError as exc:
                    # Provider failures (AI/STT/TTS) must not kill the session.
                    await self._send(websocket, error_event(exc.code, _friendly_message(exc.code)))
                    await self._send(websocket, interviewer_state("listening"))
                    done = False
                if done:
                    return

    def _parse_event(self, raw: str) -> ClientEvent:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise InvalidMessageError() from exc
        try:
            event = ClientEvent.model_validate(payload)
        except Exception as exc:  # noqa: BLE001 - pydantic ValidationError
            raise InvalidMessageError() from exc
        if event.type not in ClientEventType:
            raise InvalidMessageError()
        return event

    async def _dispatch(
        self,
        websocket: WebSocket,
        session: InterviewSession,
        event: ClientEvent,
        audio_buffer: bytearray,
    ) -> bool:
        """Handle one client event. Returns True when the loop should exit."""
        event_type = event.type
        if event_type == ClientEventType.PING:
            await self._send(websocket, ServerEvent(type=ServerEventType.PONG))
            return False
        if event_type == ClientEventType.SESSION_START:
            await self._start_interview(websocket, session)
            return False
        if event_type == ClientEventType.AUDIO_END:
            # Capture and clear BEFORE processing so a failed turn never
            # re-processes stale audio on the next audio.end.
            audio = bytes(audio_buffer)
            audio_buffer.clear()
            return await self._process_audio(websocket, session, audio)
        if event_type == ClientEventType.CANDIDATE_TEXT:
            text = self._candidate_text(event)
            if text is None:
                await self._send(
                    websocket,
                    error_event(
                        "INVALID_MESSAGE",
                        "candidate.text requires a 'text' field with the candidate's answer.",
                    ),
                )
                return False
            return await self._process_candidate_text(websocket, session, text)
        if event_type == ClientEventType.SESSION_END:
            await self._finalize_session(websocket, session)
            return True
        return False

    @staticmethod
    def _candidate_text(event: ClientEvent) -> str | None:
        if not isinstance(event.data, dict):
            return None
        text = event.data.get("text")
        if not isinstance(text, str) or not text.strip():
            return None
        return text.strip()

    # -- Interview steps ----------------------------------------------------

    async def _start_interview(self, websocket: WebSocket, session: InterviewSession) -> None:
        if session.status == SessionStatus.IN_PROGRESS:
            return
        session.status = SessionStatus.IN_PROGRESS
        session.started_at = datetime.now(UTC)
        await self._repo.update(session)
        logger.info("Interview started", extra={"session_id": session.session_id})

        opening, _ = await self._engine.get_opening(session)
        await self._repo.update(session)
        await self._say(websocket, session, opening)
        await self._send(websocket, interviewer_state("listening"))
        self._listening.add(session.session_id)

    async def _process_audio(
        self, websocket: WebSocket, session: InterviewSession, audio: bytes
    ) -> bool:
        """Process a candidate audio turn. Returns True when the interview ended."""
        # Reject turns after the interview is already completed.
        if session.status != SessionStatus.IN_PROGRESS:
            return True

        if not audio or len(audio) < self._settings.stt_min_audio_bytes:
            await self._send(
                websocket,
                error_event(
                    "AUDIO_TOO_SHORT",
                    "The audio was too short to understand. Please try again.",
                ),
            )
            await self._send(websocket, interviewer_state("listening"))
            self._listening.add(session.session_id)
            return False

        await self._send(websocket, interviewer_state("thinking"))
        self._listening.discard(session.session_id)

        try:
            result = await self._stt.transcribe(audio)
        except TranscriptionFailedError:
            await self._send(
                websocket,
                error_event(
                    "TRANSCRIPTION_FAILED",
                    "We couldn't understand that response. Please try again.",
                ),
            )
            await self._send(websocket, interviewer_state("listening"))
            self._listening.add(session.session_id)
            return False

        session.silence_count = 0
        await self._send(websocket, candidate_transcript(result.text))
        return await self._handle_candidate_turn(websocket, session, result.text)

    async def _process_candidate_text(
        self, websocket: WebSocket, session: InterviewSession, text: str
    ) -> bool:
        """Process a typed candidate answer. Returns True when the interview ended."""
        if session.status != SessionStatus.IN_PROGRESS:
            return True
        await self._send(websocket, interviewer_state("thinking"))
        self._listening.discard(session.session_id)
        await self._send(websocket, candidate_transcript(text))
        return await self._handle_candidate_turn(websocket, session, text)

    async def _handle_candidate_turn(
        self, websocket: WebSocket, session: InterviewSession, text: str
    ) -> bool:
        """Process the engine outcome. Returns True if the interview ended (loop should exit)."""
        logger.info(
            "Candidate turn processed",
            extra={"session_id": session.session_id, "turn_count": session.turn_count + 1},
        )

        outcome = await self._engine.process_candidate_turn(session, text)
        session.current_stage = outcome["stage"]
        await self._repo.update(session)

        if outcome["is_final"]:
            await self._say(websocket, session, outcome["text"])
            await self._finalize_session(websocket, session)
            return True  # interview ended → exit loop

        await self._send(
            websocket,
            interviewer_response(outcome["text"], session.current_stage or ""),
        )
        await self._say(websocket, session, outcome["text"])
        await self._send(websocket, interviewer_state("listening"))
        self._listening.add(session.session_id)
        return False

    async def _say(self, websocket: WebSocket, session: InterviewSession, text: str) -> None:
        """Stream interviewer speech: transcript event + PCM audio."""
        if not text:
            return
        await self._send(websocket, interviewer_state("speaking"))
        await self._send(websocket, interviewer_transcript(text))
        try:
            audio = await self._tts.synthesize(text)
        except TtsFailedError:
            await self._send(
                websocket,
                error_event("TTS_FAILED", "We couldn't play that message. Please try again."),
            )
            return
        await self._stream_audio(websocket, audio)

    async def _stream_audio(self, websocket: WebSocket, audio: AudioResult) -> None:
        """Emit audio.start metadata, then WAV binary frames, then audio.end."""
        sent_start = await self._send(
            websocket,
            audio_start_event(audio.format, audio.sample_rate or 24000),
        )
        if not sent_start:
            return
        try:
            for i in range(0, len(audio.audio), AUDIO_CHUNK_SIZE):
                await websocket.send_bytes(audio.audio[i : i + AUDIO_CHUNK_SIZE])
        except (WebSocketDisconnect, RuntimeError, OSError):
            # Client disconnected mid-stream, or the underlying TCP socket died
            # (ConnectionResetError/BrokenPipeError are OSErrors). Nothing more
            # to send — return without letting the exception kill the handler.
            return
        await self._send(websocket, ServerEvent(type=ServerEventType.AUDIO_END))

    async def _finalize_session(self, websocket: WebSocket, session: InterviewSession) -> None:
        if session.status == SessionStatus.COMPLETED:
            return
        session.status = SessionStatus.COMPLETED
        session.ended_at = datetime.now(UTC)
        self._listening.discard(session.session_id)
        await self._repo.update(session)
        logger.info("Interview completed", extra={"session_id": session.session_id})

        await self._send(
            websocket,
            ServerEvent(
                type=ServerEventType.SESSION_COMPLETED,
                data={"session_id": session.session_id},
            ),
        )
        await self._run_assessment(websocket, session)

    async def _run_assessment(self, websocket: WebSocket, session: InterviewSession) -> None:
        # Idempotent: never evaluate twice (the is_final path may already have
        # started a background assessment).
        if session.assessment_status in (
            AssessmentStatus.IN_PROGRESS,
            AssessmentStatus.COMPLETED,
            AssessmentStatus.FAILED,
        ):
            return
        session.assessment_status = AssessmentStatus.IN_PROGRESS
        await self._repo.update(session)
        await self._send(websocket, assessment_started())
        try:
            assessment = await self._evaluator.evaluate(session)
            session.assessment = assessment
            session.assessment_status = AssessmentStatus.COMPLETED
            await self._repo.update(session)
            await self._send(websocket, assessment_completed(session.session_id))
            logger.info("Assessment completed", extra={"session_id": session.session_id})
        except Exception:  # noqa: BLE001
            logger.warning("Assessment failed", extra={"session_id": session.session_id})
            session.assessment_status = AssessmentStatus.FAILED
            await self._repo.update(session)
            await self._send(
                websocket,
                error_event("ASSESSMENT_FAILED", "Assessment could not be generated."),
            )

    # -- Silence handling ---------------------------------------------------

    async def _silence_monitor(
        self, websocket: WebSocket, session: InterviewSession, clock: _ActivityClock
    ) -> None:
        """Prompt the candidate after configurable idle periods."""
        try:
            while True:
                await asyncio.sleep(1)
                if session.status != SessionStatus.IN_PROGRESS:
                    continue
                # Only prompt while the interviewer is actually waiting for
                # input — never during STT/AI/TTS processing.
                if session.session_id not in self._listening:
                    continue
                idle = clock.idle_seconds()
                if idle >= self._settings.max_silence_seconds and not clock.offer_sent:
                    clock.offer_sent = True
                    session.silence_count += 1
                    await self._repo.update(session)
                    await self._send(websocket, silence_prompt(SILENCE_OFFER_CHANCE))
                elif idle >= self._settings.silence_prompt_seconds and not clock.silence_prompt_sent:
                    clock.silence_prompt_sent = True
                    await self._send(websocket, silence_prompt(SILENCE_GENTLE))
        except asyncio.CancelledError:
            return

    # -- Helpers ------------------------------------------------------------

    async def _send(self, websocket: WebSocket, event: ServerEvent) -> bool:
        """Send an event. Returns False if the client is no longer connected."""
        try:
            await websocket.send_text(event.model_dump_json(exclude_none=True))
            return True
        except (WebSocketDisconnect, RuntimeError):
            # Client disconnected or the connection is closing; nothing more to do.
            return False

    async def _reject(self, websocket: WebSocket, code: str, message: str) -> None:
        await websocket.accept()
        await self._send(websocket, error_event(code, message))
        await websocket.close(code=1008)
