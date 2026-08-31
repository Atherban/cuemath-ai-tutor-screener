from __future__ import annotations

import logging
from typing import Any

from app.core.config import Settings
from app.models.session import (
    InterviewSession,
    SessionStatus,
    TranscriptEntry,
)
from app.services.ai.base import AIProvider
from app.services.interview.abuse_detector import detect_abuse, non_cooperation_closing
from app.services.interview.prompts import (
    CLOSING_TEMPLATE,
    EARLY_TERMINATION_MARKER,
    OPENING_TEMPLATE,
    SKIP_MARKER,
    TIME_UP_SIGNAL,
    build_stage_prompt,
)
from app.services.interview.state import (
    InterviewAction,
    InterviewStage,
    dimension_for_stage,
    next_stage,
)

logger = logging.getLogger(__name__)


class InterviewEngine:
    """Structured 5-stage interview (one question per stage).

    INTRO → SIMPLIFICATION → ROLEPLAY → METHODOLOGY → SCENARIO → CLOSING

    Each stage asks exactly ONE AI-personalised question. There is no follow-up
    drilling — the interview moves through stages deterministically, covering
    the five soft-skill dimensions. The AI generates questions from per-stage
    directives, so they are always personalised to the candidate's answers.
    """

    def __init__(self, settings: Settings, ai_provider: AIProvider) -> None:
        self._settings = settings
        self._ai = ai_provider
        self._max_total_questions = settings.max_total_questions

    async def get_opening(self, session: InterviewSession) -> tuple[str, str]:
        """Return (transcript_text, action) for the interview opening."""
        session.current_stage = InterviewStage.INTRO.value
        return OPENING_TEMPLATE, InterviewAction.ASK_PRIMARY.value

    async def process_candidate_turn(
        self, session: InterviewSession, candidate_text: str
    ) -> dict[str, Any]:
        session.turn_count += 1

        if self.should_end(session):
            return await self._end_interview(session)

        # Per-question timer expired with no answer → record and advance.
        if candidate_text.strip() == SKIP_MARKER:
            self._append_transcript(session, "candidate", "(no response)", session.current_stage)
            stage = InterviewStage(session.current_stage) if session.current_stage else InterviewStage.INTRO
            next_st = next_stage(stage)
            if next_st is None:
                return await self._end_interview(session)
            return await self._transition_to(session, next_st, "(no response)")

        # TIME_IS_UP_SIGNAL → conclude immediately.
        if TIME_UP_SIGNAL in candidate_text.upper():
            return await self._end_interview(session)

        # Abuse detection — deterministic, always runs first.
        abuse_reason = detect_abuse(candidate_text)
        if abuse_reason:
            return await self._end_interview_early(
                session, non_cooperation_closing(), "CANDIDATE_NON_COOPERATION"
            )

        # Append candidate's turn.
        self._append_transcript(session, "candidate", candidate_text, session.current_stage)

        stage = InterviewStage(session.current_stage) if session.current_stage else InterviewStage.INTRO

        # Move to next stage.
        next_st = next_stage(stage)
        if next_st is None:
            return await self._end_interview(session)

        return await self._transition_to(session, next_st, candidate_text)

    async def _transition_to(
        self, session: InterviewSession, target: InterviewStage, last_response: str
    ) -> dict[str, Any]:
        session.current_stage = target.value

        # Mark the current stage's dimension as covered.
        dim = dimension_for_stage(target)
        if dim and dim not in session.topics_covered:
            session.topics_covered.append(dim)

        if target == InterviewStage.CLOSING:
            text = CLOSING_TEMPLATE
            self._append_transcript(session, "interviewer", text, target.value)
            return {
                "action": InterviewAction.END_INTERVIEW.value,
                "text": text,
                "stage": target.value,
                "is_final": True,
            }

        if target == InterviewStage.ASSESSMENT:
            return {
                "action": InterviewAction.END_INTERVIEW.value,
                "text": "",
                "stage": target.value,
                "is_final": True,
            }

        # Ask the AI for the personalised question for this stage.
        text = await self._ai_question(target.value, session)
        if _is_termination(text):
            closing = _strip_termination(text) or CLOSING_TEMPLATE
            return await self._end_interview_early(
                session, closing, "CANDIDATE_NON_COOPERATION"
            )

        self._append_transcript(session, "interviewer", text, target.value)
        logger.info(
            "Stage question asked",
            extra={
                "session_id": session.session_id,
                "stage": target.value,
                "dimension": dim,
                "question": text[:100],
            },
        )
        return {
            "action": InterviewAction.ASK_PRIMARY.value,
            "text": text,
            "stage": target.value,
            "is_final": False,
        }

    async def _ai_question(self, stage: str, session: InterviewSession) -> str:
        """Generate ONE independent, parameter-specific question for the stage."""
        try:
            prompt = build_stage_prompt(stage, "")
            raw = (await self._ai.generate_text(prompt)).strip()
            return _single_question(raw)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "AI question generation failed for stage %s",
                stage,
                extra={"session_id": session.session_id, "error": type(exc).__name__},
            )
            return "Let's move on. Could you tell me about your approach to teaching?"

    async def _end_interview(self, session: InterviewSession) -> dict[str, Any]:
        text = CLOSING_TEMPLATE
        self._append_transcript(session, "interviewer", text, InterviewStage.CLOSING.value)
        return {
            "action": InterviewAction.END_INTERVIEW.value,
            "text": text,
            "stage": InterviewStage.CLOSING.value,
            "is_final": True,
        }

    async def _end_interview_early(
        self, session: InterviewSession, closing_text: str, reason: str
    ) -> dict[str, Any]:
        session.fail_reason = reason
        self._append_transcript(session, "interviewer", closing_text, session.current_stage)
        logger.info(
            "Interview terminated early",
            extra={"session_id": session.session_id, "reason": reason, "turn_count": session.turn_count},
        )
        return {
            "action": InterviewAction.END_INTERVIEW.value,
            "text": closing_text,
            "stage": session.current_stage,
            "is_final": True,
        }

    def _append_transcript(
        self, session: InterviewSession, role: str, text: str, stage: str | None
    ) -> None:
        session.conversation_history.append(
            TranscriptEntry(role=role, text=text, stage=stage)
        )

    def should_end(self, session: InterviewSession) -> bool:
        return (
            session.turn_count >= self._max_total_questions
            or session.status == SessionStatus.COMPLETED
        )


def _is_termination(text: str) -> bool:
    return EARLY_TERMINATION_MARKER in text


def _strip_termination(text: str) -> str:
    return text.split(EARLY_TERMINATION_MARKER)[0].strip()


def _single_question(text: str) -> str:
    """Ensure the AI produced exactly ONE question.

    The AI is instructed to ask one question per stage, but small models can
    ignore that. As a hard guard we keep only the text up to and including the
    first question mark, dropping any trailing second question or commentary.
    """
    if not text:
        return text
    idx = text.find("?")
    if idx == -1:
        return text
    return text[: idx + 1].strip()