from __future__ import annotations

from dataclasses import dataclass, field

from app.models.assessment import Recommendation


@dataclass(frozen=True)
class DimensionDefinition:
    key: str
    label: str
    description: str
    positive_indicators: list[str]
    negative_indicators: list[str]


DIMENSIONS: dict[str, DimensionDefinition] = {
    "clarity": DimensionDefinition(
        key="clarity",
        label="Communication Clarity",
        description="How clearly and logically the candidate structures their explanations.",
        positive_indicators=[
            "Explains steps in a logical order",
            "Uses concrete examples to illustrate ideas",
            "Checks for understanding",
            "Avoids unnecessary jargon or explains it",
        ],
        negative_indicators=[
            "Vague, rambling, or contradictory explanations",
            "Skips logical steps",
            "Relies on jargon without explaining it",
        ],
    ),
    "simplicity": DimensionDefinition(
        key="simplicity",
        label="Simplicity",
        description="Ability to break down concepts so a young learner can follow.",
        positive_indicators=[
            "Uses age-appropriate language",
            "Draws on real-world analogies (food, toys, everyday objects)",
            "Builds up from a single simple idea",
        ],
        negative_indicators=[
            "Explains at an advanced level without scaffolding",
            "Cannot simplify when asked",
        ],
    ),
    "patience": DimensionDefinition(
        key="patience",
        label="Patience",
        description="Responds calmly and constructively when a student is stuck.",
        positive_indicators=[
            "Diagnoses the specific difficulty before re-teaching",
            "Does not repeat the same explanation verbatim",
            "Gives the student time and re-frames the problem",
        ],
        negative_indicators=[
            "Frustration or blame directed at the student",
            "Repeats the same explanation without adaptation",
            "Gives up or tells the student to 'just get it'",
        ],
    ),
    "warmth": DimensionDefinition(
        key="warmth",
        label="Warmth / Empathy",
        description="Validates student feelings and supports motivation.",
        positive_indicators=[
            "Acknowledges the student's frustration or effort",
            "Uses encouraging language without empty flattery",
            "Helps the student see mistakes as part of learning",
        ],
        negative_indicators=[
            "Dismisses the student's feelings",
            "Puts performance pressure on the student",
            "Makes the student feel bad about mistakes",
        ],
    ),
    "fluency": DimensionDefinition(
        key="fluency",
        label="English Fluency",
        description=(
            "Comprehensibility, vocabulary range, and sentence construction — "
            "NOT accent, regional origin, or native-speaker status."
        ),
        positive_indicators=[
            "Expresses ideas coherently and completely",
            "Uses appropriate vocabulary for the situation",
            "Communicates an idea even when phrased simply",
        ],
        negative_indicators=[
            "Speech so disjointed the idea is not conveyed",
            "Inability to express a basic idea",
        ],
    ),
}
@dataclass
class EvidenceDatum:
    quote: str
    reason: str


@dataclass
class DimensionVerdict:
    score: float
    confidence: float
    summary: str
    strengths: list[str] = field(default_factory=list)
    concerns: list[str] = field(default_factory=list)
    evidence: list[EvidenceDatum] = field(default_factory=list)
    evidence_status: str = "SUFFICIENT"


@dataclass
class AssessmentVerdict:
    dimensions: dict[str, DimensionVerdict]
    key_strengths: list[str] = field(default_factory=list)
    key_concerns: list[str] = field(default_factory=list)
    overall_score: float = 0.0
    confidence: float = 0.0
    summary: str = ""
    recommendation: Recommendation = Recommendation.BORDERLINE


def evidence_coverage(verdict: AssessmentVerdict) -> float:
    """Fraction of dimensions with sufficient or partial evidence."""
    if not verdict.dimensions:
        return 0.0
    covered = sum(
        1 for d in verdict.dimensions.values() if d.evidence_status in ("SUFFICIENT", "PARTIAL")
    )
    return covered / len(verdict.dimensions)


def decide_recommendation(verdict: AssessmentVerdict) -> Recommendation:
    """Rule-based recommendation grounded in scores, confidence, and evidence.

    Uses a weighted overall score but refuses strong signals when evidence is
    missing or confidence is low.
    """
    coverage = evidence_coverage(verdict)
    avg_confidence = (
        sum(d.confidence for d in verdict.dimensions.values()) / len(verdict.dimensions)
        if verdict.dimensions
        else 0.0
    )

    # Insufficient evidence → cannot recommend strongly in either direction.
    if coverage < 0.4 or avg_confidence < 0.35:
        return Recommendation.BORDERLINE

    score = verdict.overall_score

    # Serious concerns cap the recommendation.
    serious_concerns = any(
        "not" in c.lower() or "fails" in c.lower() or "repeats" in c.lower()
        for c in verdict.key_concerns
    )

    if score >= 8.0 and not serious_concerns:
        return Recommendation.STRONG_PROCEED
    if score >= 6.5:
        return Recommendation.PROCEED
    if score >= 4.5:
        return Recommendation.BORDERLINE
    return Recommendation.DO_NOT_PROCEED
