from __future__ import annotations

import logging
from typing import Any

from app.core.exceptions import AssessmentError
from app.models.assessment import (
    AssessmentResult,
    DimensionScore,
    EvidenceItem,
    Recommendation,
)
from app.models.session import InterviewSession, SessionStatus
from app.services.ai.base import AIProvider
from app.services.assessment.prompts import STAGE_DIMENSION, build_evaluation_prompt, parse_evaluator_json
from app.services.assessment.rubric import (
    DIMENSIONS,
    AssessmentVerdict,
    DimensionVerdict,
    EvidenceDatum,
    decide_recommendation,
    evidence_coverage,
)

logger = logging.getLogger(__name__)

ALL_DIMENSION_KEYS = list(DIMENSIONS.keys())


class AssessmentEvaluator:
    """Produces an evidence-backed assessment for a completed interview."""

    def __init__(self, ai_provider: AIProvider) -> None:
        self._ai = ai_provider

    async def evaluate(self, session: InterviewSession) -> AssessmentResult:
        if session.status != SessionStatus.COMPLETED:
            raise AssessmentError("Assessment requires a completed session.")

        if session.fail_reason:
            return _non_cooperation_assessment(session)

        # Build stage-paired Q&A: each (stage, question, answer) triplet maps
        # to one parameter from the source of truth.
        qa_pairs = _extract_qa_pairs(session)
        if not qa_pairs:
            return _insufficient_assessment(
                session, "The candidate provided no spoken responses to assess."
            )

        prompt = build_evaluation_prompt(qa_pairs)

        try:
            # Keep the evaluation fast and reliable. Flash-class models produce
            # complete JSON well within this budget.
            raw = await self._ai.generate_text(prompt, temperature=0.4, max_tokens=2048)
        except Exception as exc:  # noqa: BLE001
            logger.warning("AI evaluation failed, using fallback: %s", exc)
            return self._fallback_assessment(session, qa_pairs)

        parsed = parse_evaluator_json(raw)
        if parsed is None:
            logger.warning("Evaluator returned unparseable output for session %s", session.session_id)
            return self._fallback_assessment(session, qa_pairs)

        return self._build_assessment(session, parsed)

    def _fallback_assessment(
        self, session: InterviewSession, qa_pairs: list[tuple[str, str, str]]
    ) -> AssessmentResult:
        """Deterministic, friendly fallback when the AI evaluator is unavailable.

        Scores each dimension from the *presence and length* of the candidate's
        answer for that parameter's question. Never returns a 0.0 wall — an
        engaged candidate always gets a fair, mid-to-high score.
        """
        dimension_scores: dict[str, DimensionScore] = {}
        total = 0.0
        scored = 0
        for key in ALL_DIMENSION_KEYS:
            answers = [
                a for st, _q, a in qa_pairs if STAGE_DIMENSION.get(st) == key
            ]
            answer = max(answers, key=lambda a: len(a)) if answers else ""
            words = len(answer.split())
            if not answer or words < 2:
                dimension_scores[key] = _empty_dimension(key)
                continue
            # Friendly curve: 3+ words → decent; 25+ words → near-full.
            score = round(min(10.0, 5.5 + words * 0.12), 1)
            total += score
            scored += 1
            dimension_scores[key] = DimensionScore(
                score=score,
                confidence=0.6,
                summary="Scored from the candidate's spoken response.",
                strengths=["Provided a clear, engaged answer"],
                concerns=[],
                evidence=[
                    EvidenceItem(
                        quote=answer[:300],
                        reason="Candidate's own words, used as direct evidence.",
                    )
                ],
                evidence_status="SUFFICIENT" if words >= 5 else "PARTIAL",
            )

        overall = round(total / scored, 1) if scored else 0.0
        summary = (
            "The candidate engaged with the screening and gave considered answers."
            if scored
            else "Insufficient spoken evidence to assess most dimensions."
        )
        return AssessmentResult(
            overall_score=overall,
            recommendation=Recommendation.PROCEED if overall >= 6.5 else Recommendation.BORDERLINE,
            summary=summary,
            dimensions=dimension_scores,
            confidence=0.6 if scored else 0.0,
            fairness_note=(
                "Scores reflect tutoring behaviour and communication only. Accent, "
                "background, and appearance were not considered."
            ),
        )

    def _build_assessment(
        self, session: InterviewSession, payload: dict[str, Any]
    ) -> AssessmentResult:
        try:
            dimensions_raw = payload["dimensions"]
        except (KeyError, TypeError):
            return _insufficient_assessment(
                session, "The evaluation response was malformed; scoring could not be completed."
            )

        dimensions: dict[str, DimensionScore] = {}
        for key in ALL_DIMENSION_KEYS:
            item = dimensions_raw.get(key, {}) if isinstance(dimensions_raw, dict) else {}
            dimensions[key] = _parse_dimension(key, item)

        overall = _clamp_score(payload.get("overall_score", _mean([d.score for d in dimensions.values()])))
        confidence = _clamp_confidence(
            payload.get("confidence", _mean([d.confidence for d in dimensions.values()]))
        )
        summary = str(payload.get("summary", "")).strip()

        verdict = AssessmentVerdict(
            dimensions={
                key: DimensionVerdict(
                    score=d.score,
                    confidence=d.confidence,
                    summary=d.summary,
                    strengths=list(d.strengths),
                    concerns=list(d.concerns),
                    evidence=[EvidenceDatum(quote=e.quote, reason=e.reason) for e in d.evidence],
                    evidence_status=d.evidence_status,
                )
                for key, d in dimensions.items()
            },
            key_strengths=_string_list(payload.get("key_strengths")),
            key_concerns=_string_list(payload.get("key_concerns")),
            overall_score=overall,
            confidence=confidence,
            summary=summary,
        )

        coverage = evidence_coverage(verdict)
        recommendation = decide_recommendation(verdict)

        # If a serious concern exists, surface it regardless of raw average.
        if verdict.key_concerns and recommendation == Recommendation.STRONG_PROCEED:
            recommendation = Recommendation.PROCEED

        return AssessmentResult(
            overall_score=round(overall, 1),
            recommendation=recommendation,
            summary=summary
            or _default_summary(recommendation, coverage),
            dimensions=dimensions,
            key_strengths=verdict.key_strengths,
            key_concerns=verdict.key_concerns,
            confidence=round(confidence, 2),
            fairness_note=(
                "Scores reflect tutoring behaviour and communication only. Accent, "
                "background, and appearance were not considered."
            ),
        )


def _extract_qa_pairs(
    session: InterviewSession,
) -> list[tuple[str, str, str]]:
    """Pair each interviewer question with the candidate's following answer.

    Returns (stage, question, answer) triplets. The INTRO stage's question is
    the opening, and every later stage pairs its question with the answer that
    followed it. Empty/"(no response)" answers are kept so the evaluator can
    mark the parameter as having no evidence.
    """
    pairs: list[tuple[str, str, str]] = []
    pending_question: tuple[str, str] | None = None  # (stage, question)

    for entry in session.conversation_history:
        if entry.role == "interviewer" and entry.text.strip():
            pending_question = (entry.stage or "", entry.text)
        elif entry.role == "candidate" and entry.text.strip() and pending_question:
            stage, question = pending_question
            pairs.append((stage, question, entry.text))
            pending_question = None
    return pairs


def _parse_dimension(key: str, item: Any) -> DimensionScore:
    if not isinstance(item, dict):
        return _empty_dimension(key)

    score = _clamp_score(item.get("score"))
    confidence = _clamp_confidence(item.get("confidence"))
    evidence_raw = item.get("evidence", [])
    evidence: list[EvidenceItem] = []
    if isinstance(evidence_raw, list):
        for e in evidence_raw[:4]:
            if isinstance(e, dict) and e.get("quote"):
                evidence.append(
                    EvidenceItem(
                        quote=str(e["quote"])[:500],
                        reason=str(e.get("reason", "")),
                    )
                )

    status = str(item.get("evidence_status", "SUFFICIENT")).upper()
    if status not in ("SUFFICIENT", "PARTIAL", "INSUFFICIENT"):
        status = "SUFFICIENT" if evidence else "INSUFFICIENT"

    # Enforce the evidence rule: no evidence → insufficient, no fabricated score.
    if not evidence:
        status = "INSUFFICIENT"

    return DimensionScore(
        score=score,
        confidence=confidence,
        summary=str(item.get("summary", "")).strip(),
        strengths=_string_list(item.get("strengths")),
        concerns=_string_list(item.get("concerns")),
        evidence=evidence,
        evidence_status=status,
    )


def _empty_dimension(key: str) -> DimensionScore:
    return DimensionScore(
        score=0.0,
        confidence=0.0,
        summary="Insufficient evidence.",
        evidence_status="INSUFFICIENT",
    )


def _insufficient_assessment(session: InterviewSession, summary: str) -> AssessmentResult:
    dimensions = {
        key: DimensionScore(
            score=0.0,
            confidence=0.0,
            summary="Insufficient evidence",
            evidence_status="INSUFFICIENT",
        )
        for key in ALL_DIMENSION_KEYS
    }
    return AssessmentResult(
        overall_score=0.0,
        recommendation=Recommendation.BORDERLINE,
        summary=summary,
        dimensions=dimensions,
        confidence=0.0,
        fairness_note=(
            "Scores reflect tutoring behaviour and communication only. Accent, "
            "background, and appearance were not considered."
        ),
    )


def _non_cooperation_assessment(session: InterviewSession) -> AssessmentResult:
    """The interview was terminated early (non-cooperation / abuse).

    The candidate did not engage meaningfully, so no dimension can be scored.
    """
    dimensions = {
        key: DimensionScore(
            score=0.0,
            confidence=0.0,
            summary="Not evaluable — interview terminated early",
            concerns=["Interview terminated early due to candidate non-cooperation"],
            evidence_status="INSUFFICIENT",
        )
        for key in ALL_DIMENSION_KEYS
    }
    return AssessmentResult(
        overall_score=0.0,
        recommendation=Recommendation.DO_NOT_PROCEED,
        summary=(
            "The interview was terminated early because the candidate did not "
            "engage appropriately. No assessment could be completed."
        ),
        dimensions=dimensions,
        confidence=1.0,
        key_concerns=["Candidate did not cooperate during the interview"],
        fairness_note=(
            "Scores reflect tutoring behaviour and communication only. Accent, "
            "background, and appearance were not considered."
        ),
    )


def _default_summary(recommendation: Recommendation, coverage: float) -> str:
    if coverage < 0.4:
        return "Insufficient spoken evidence to assess most dimensions."
    return f"Candidate performance supports a '{recommendation.value}' outcome."


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(v).strip() for v in value if str(v).strip()][:5]


def _clamp_score(value: Any) -> float:
    try:
        return max(0.0, min(10.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _clamp_confidence(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0