from __future__ import annotations

import json

import pytest

from app.models.assessment import Recommendation
from app.models.session import AssessmentStatus, InterviewSession, SessionStatus, TranscriptEntry
from app.services.assessment.evaluator import AssessmentEvaluator

VALID_EVALUATOR_OUTPUT = json.dumps(
    {
        "dimensions": {
            "clarity": {
                "score": 8,
                "confidence": 0.9,
                "summary": "Clear step-by-step explanations.",
                "strengths": ["Logical order"],
                "concerns": [],
                "evidence": [
                    {"quote": "I would split a pizza into two equal parts.",
                     "reason": "Uses a concrete demonstration."}
                ],
                "evidence_status": "SUFFICIENT",
            },
            "simplicity": {
                "score": 9,
                "confidence": 0.9,
                "summary": "Age-appropriate analogies.",
                "strengths": [],
                "concerns": [],
                "evidence": [
                    {"quote": "I'd draw it on paper and count the pieces together.",
                     "reason": "Scaffolds for a young learner."}
                ],
                "evidence_status": "SUFFICIENT",
            },
            "patience": {
                "score": 8,
                "confidence": 0.85,
                "summary": "Diagnoses before re-teaching.",
                "strengths": [],
                "concerns": [],
                "evidence": [
                    {"quote": "If the child doesn't get it, I'd draw it on paper.",
                     "reason": "Adapts rather than repeating."}
                ],
                "evidence_status": "SUFFICIENT",
            },
            "warmth": {
                "score": 7,
                "confidence": 0.8,
                "summary": "Encouraging language.",
                "strengths": [],
                "concerns": [],
                "evidence": [
                    {"quote": "Everyone can learn with practice.",
                     "reason": "Growth-mindset encouragement."}
                ],
                "evidence_status": "SUFFICIENT",
            },
            "fluency": {
                "score": 8,
                "confidence": 0.9,
                "summary": "Coherent and complete answers.",
                "strengths": [],
                "concerns": [],
                "evidence": [
                    {"quote": "If my first explanation fails, I'd try using their favourite example.",
                     "reason": "Full sentence construction."}
                ],
                "evidence_status": "SUFFICIENT",
            },
            "adaptability": {
                "score": 8,
                "confidence": 0.85,
                "summary": "Tries a different approach.",
                "strengths": [],
                "concerns": [],
                "evidence": [
                    {"quote": "I'd try using their favourite example instead.",
                     "reason": "Switches strategy."}
                ],
                "evidence_status": "SUFFICIENT",
            },
        },
        "key_strengths": ["Concrete examples", "Diagnostic approach"],
        "key_concerns": [],
        "overall_score": 8.0,
        "confidence": 0.85,
        "summary": "Strong candidate with clear tutoring instincts.",
    }
)


def _completed_session() -> InterviewSession:
    session = InterviewSession()
    session.status = SessionStatus.COMPLETED
    session.assessment_status = AssessmentStatus.PENDING
    for text in [
        "I would split a pizza into two equal parts and say each part is one half.",
        "If the child doesn't get it, I'd draw it on paper and count the pieces together.",
        "If they say they are bad at math, I'd say everyone can learn with practice.",
        "If my first explanation fails, I'd try using their favourite example instead.",
    ]:
        session.conversation_history.append(TranscriptEntry(role="candidate", text=text, stage="x"))
        session.conversation_history.append(
            TranscriptEntry(role="interviewer", text="Tell me more.", stage="x")
        )
    return session


async def test_valid_transcript_produces_assessment(fake_ai):
    fake_ai.enqueue(VALID_EVALUATOR_OUTPUT)
    evaluator = AssessmentEvaluator(fake_ai)
    result = await evaluator.evaluate(_completed_session())

    assert set(result.dimensions.keys()) == {
        "clarity", "simplicity", "patience", "warmth", "fluency"
    }
    assert result.overall_score == 8.0
    assert result.recommendation in (
        Recommendation.STRONG_PROCEED,
        Recommendation.PROCEED,
    )
    assert all(d.evidence_status == "SUFFICIENT" for d in result.dimensions.values())
    assert all(d.evidence for d in result.dimensions.values())
    assert result.fairness_note


async def test_insufficient_evidence_marks_dimensions(fake_ai):
    fake_ai.enqueue(
        json.dumps(
            {
                "dimensions": {
                    k: {
                        "score": 0,
                        "confidence": 0.0,
                        "summary": "No evidence",
                        "strengths": [],
                        "concerns": [],
                        "evidence": [],
                        "evidence_status": "INSUFFICIENT",
                    }
                    for k in [
                        "clarity", "simplicity", "patience", "warmth", "fluency"
                    ]
                },
                "key_strengths": [],
                "key_concerns": [],
                "overall_score": 0.0,
                "confidence": 0.0,
                "summary": "No evidence available.",
            }
        )
    )
    evaluator = AssessmentEvaluator(fake_ai)
    result = await evaluator.evaluate(_completed_session())
    assert all(d.evidence_status == "INSUFFICIENT" for d in result.dimensions.values())
    assert result.recommendation == Recommendation.BORDERLINE


async def test_malformed_ai_output_falls_back(fake_ai):
    fake_ai.enqueue("this is not json at all")
    evaluator = AssessmentEvaluator(fake_ai)
    result = await evaluator.evaluate(_completed_session())
    assert all(d.evidence_status == "INSUFFICIENT" for d in result.dimensions.values())
    assert result.overall_score == 0.0


async def test_evaluator_rejects_incomplete_session(fake_ai):
    session = _completed_session()
    session.status = SessionStatus.IN_PROGRESS
    evaluator = AssessmentEvaluator(fake_ai)
    from app.core.exceptions import AssessmentError

    with pytest.raises(AssessmentError):
        await evaluator.evaluate(session)


async def test_evaluator_no_candidate_turns(fake_ai):
    session = InterviewSession()
    session.status = SessionStatus.COMPLETED
    evaluator = AssessmentEvaluator(fake_ai)
    result = await evaluator.evaluate(session)
    assert result.overall_score == 0.0
    assert "no spoken responses" in result.summary.lower()


async def test_score_clamping_and_evidence_rule(fake_ai):
    fake_ai.enqueue(
        json.dumps(
            {
                "dimensions": {
                    "clarity": {
                        "score": 99,
                        "confidence": 5.0,
                        "summary": "",
                        "strengths": [],
                        "concerns": [],
                        "evidence": [{"quote": "a quote", "reason": "a reason"}],
                        "evidence_status": "SUFFICIENT",
                    }
                },
                "overall_score": -3,
                "confidence": 9,
                "summary": "",
            }
        )
    )
    evaluator = AssessmentEvaluator(fake_ai)
    result = await evaluator.evaluate(_completed_session())
    assert result.dimensions["clarity"].score == 10.0
    assert result.dimensions["clarity"].confidence == 1.0
    # Missing dimensions default to insufficient.
    assert result.dimensions["simplicity"].evidence_status == "INSUFFICIENT"


async def test_evidence_never_invented_when_absent(fake_ai):
    fake_ai.enqueue(
        json.dumps(
            {
                "dimensions": {
                    k: {
                        "score": 8,
                        "confidence": 0.8,
                        "summary": "",
                        "strengths": [],
                        "concerns": [],
                        "evidence": [],  # no quotes provided
                        "evidence_status": "SUFFICIENT",  # claims sufficient
                    }
                    for k in [
                        "clarity", "simplicity", "patience", "warmth", "fluency"
                    ]
                },
                "overall_score": 8,
                "confidence": 0.8,
                "summary": "",
            }
        )
    )
    evaluator = AssessmentEvaluator(fake_ai)
    result = await evaluator.evaluate(_completed_session())
    # Evidence rule: no quotes => forced to INSUFFICIENT despite claim.
    assert all(d.evidence_status == "INSUFFICIENT" for d in result.dimensions.values())
