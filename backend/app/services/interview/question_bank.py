from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field

from app.models.assessment import Recommendation


@dataclass
class QuestionTemplate:
    id: str
    dimension: str
    primary: str
    followups: list[str] = field(default_factory=list)
    min_expectation: str = ""


DIMENSIONS = [
    "clarity",
    "simplicity",
    "patience",
    "warmth",
    "fluency",
    "adaptability",
]

TEMPLATES: list[QuestionTemplate] = [
    QuestionTemplate(
        id="simplicity_1",
        dimension="simplicity",
        primary="Imagine you're teaching fractions to a nine-year-old who has never seen them before. How would you explain what one-half means?",
        followups=[
            "What if the child still doesn't get it after the first explanation?",
            "Can you think of a real-world object you'd use to demonstrate one-half?",
            "How would you check if they actually understood?",
        ],
        min_expectation="Uses a concrete analogy or visual language appropriate for a child.",
    ),
    QuestionTemplate(
        id="simplicity_2",
        dimension="simplicity",
        primary="How would you explain the concept of area to a ten-year-old who is just learning multiplication?",
        followups=[
            "What if they confuse area with perimeter?",
            "What everyday example would you reach for first?",
        ],
        min_expectation="Breaks down a geometric concept into relatable steps.",
    ),
    QuestionTemplate(
        id="patience_1",
        dimension="patience",
        primary="A student has been staring at a problem for five minutes and finally says, 'I don't understand.' What would you do?",
        followups=[
            "What if after you explain, they still look confused?",
            "How would you tell the difference between a student who is stuck and one who is simply not trying?",
            "What would you say to keep them from feeling discouraged?",
        ],
        min_expectation="Describes a diagnostic approach rather than repeating the same instruction.",
    ),
    QuestionTemplate(
        id="patience_2",
        dimension="patience",
        primary="A student keeps making the same mistake on a type of problem, even after you've explained it three times. How would you handle it?",
        followups=[
            "Would you change your approach? How?",
            "At what point would you move on to a different topic?",
        ],
        min_expectation="Shows willingness to adapt rather than repeating the same explanation.",
    ),
    QuestionTemplate(
        id="warmth_1",
        dimension="warmth",
        primary="A student says, 'I'm just bad at math. My whole family is.' How would you respond?",
        followups=[
            "What would you say to help them see that math ability can grow?",
            "How would you balance encouragement with honest feedback?",
        ],
        min_expectation="Validates the student's feeling while offering a growth-mindset perspective.",
    ),
    QuestionTemplate(
        id="warmth_2",
        dimension="warmth",
        primary="A student gets an answer right but says, 'That was just luck.' How would you handle that?",
        followups=[
            "How would you help them internalize their own success?",
            "What if they keep attributing their success to luck?",
        ],
        min_expectation="Reinforces the student's effort and capability, not just outcome.",
    ),
    QuestionTemplate(
        id="adaptability_1",
        dimension="adaptability",
        primary="You explained a concept using a visual method, but the student says they learn better by listening. What would you do?",
        followups=[
            "What if you don't have a prepared auditory explanation?",
            "How would you figure out each student's learning preference early on?",
        ],
        min_expectation="Shifts instruction style based on the student's stated preference.",
    ),
    QuestionTemplate(
        id="adaptability_2",
        dimension="adaptability",
        primary="A student asks a question that is beyond what you planned to cover today. How would you handle it?",
        followups=[
            "What if answering it would confuse them about the current topic?",
            "How would you decide whether to explore the digression or stay on track?",
        ],
        min_expectation="Balances the student's curiosity with the learning objective.",
    ),
    QuestionTemplate(
        id="clarity_1",
        dimension="clarity",
        primary="Can you walk me through how you would explain negative numbers to a beginner?",
        followups=[
            "What's the most common confusion students have with negative numbers?",
            "How would you make the explanation more concrete?",
        ],
        min_expectation="Structures the explanation in a logical step-by-step sequence.",
    ),
    QuestionTemplate(
        id="clarity_2",
        dimension="clarity",
        primary="A student says they understand the steps but keep getting the wrong answer. How would you diagnose the problem?",
        followups=[
            "What specific questions would you ask to pinpoint the misunderstanding?",
            "How would you explain the correct approach without just repeating the steps?",
        ],
        min_expectation="Diagnoses the specific misunderstanding rather than re-teaching generally.",
    ),
    QuestionTemplate(
        id="fluency_1",
        dimension="fluency",
        primary="Tell me about a time you helped someone understand something difficult. It doesn't have to be math.",
        followups=[
            "What did you say to make it click for them?",
            "How did you know they truly understood?",
        ],
        min_expectation="Communicates the experience coherently with relevant detail.",
    ),
    QuestionTemplate(
        id="fluency_2",
        dimension="fluency",
        primary="What do you enjoy most about working with young learners, and why do you think you'd be a good fit as a maths tutor?",
        followups=[
            "Can you describe a specific moment with a student that stood out to you?",
            "How do you normally build rapport with a new student?",
        ],
        min_expectation="Speaks coherently about their motivation and fit.",
    ),
    QuestionTemplate(
        id="fluency_3",
        dimension="fluency",
        primary="Walk me through how you would welcome a brand-new student into their very first session.",
        followups=[
            "How would you explain what you'll be doing together?",
            "How would you make them feel comfortable if they were nervous?",
        ],
        min_expectation="Gives a clear, structured, warm walkthrough.",
    ),
    QuestionTemplate(
        id="empathy_1",
        dimension="warmth",
        primary="A student is frustrated because they feel pressure to get perfect scores. How would you support them?",
        followups=[
            "How would you discuss the role of mistakes in learning?",
            "What if their parents are the source of the pressure?",
        ],
        min_expectation="Shows emotional attunement and practical support strategies.",
    ),
    QuestionTemplate(
        id="warmth_3",
        dimension="warmth",
        primary="A young student bursts into tears because they got a problem wrong in front of their friends. How would you handle that moment?",
        followups=[
            "How would you help them feel safe to try again?",
            "What would you say to the rest of the group about mistakes?",
        ],
        min_expectation="Responds with empathy before addressing the math.",
    ),
    QuestionTemplate(
        id="patience_3",
        dimension="patience",
        primary="A student gives up after one failed attempt and says they don't want to continue. What do you do?",
        followups=[
            "How would you convince them to try once more without forcing them?",
            "What would make you pause the session and step back?",
        ],
        min_expectation="Balances persistence with respect for the student's feelings.",
    ),
    QuestionTemplate(
        id="simplicity_3",
        dimension="simplicity",
        primary="How would you explain the idea of multiplication as repeated addition to a first-timer, using only everyday objects?",
        followups=[
            "What would you do if they thought multiplication was just 'bigger numbers'?",
            "How would you introduce the multiplication symbol without confusing them?",
        ],
        min_expectation="Builds the concept concretely from a single familiar idea.",
    ),
    QuestionTemplate(
        id="clarity_3",
        dimension="clarity",
        primary="How would you explain the difference between a square and a rectangle so a student never mixes them up again?",
        followups=[
            "What visual or hands-on activity would you use?",
            "How would you test their understanding at the end?",
        ],
        min_expectation="Distinguishes the two concepts clearly and simply.",
    ),
    QuestionTemplate(
        id="adaptability_3",
        dimension="adaptability",
        primary="Your go-to explanation isn't landing because the student is distracted and fidgety today. How do you adjust?",
        followups=[
            "How would you re-engage them without losing the lesson?",
            "When would you decide to change the activity altogether?",
        ],
        min_expectation="Recognises the student's state and adapts the approach.",
    ),
]


def _make_rng(session_id: str) -> random.Random:
    """Deterministic per-session RNG seeded from the session id.

    Different sessions get different question orderings even when the server
    is restarted (the seed is the session id, not wall-clock time).
    """
    seed = int(hashlib.sha256(session_id.encode()).hexdigest()[:8], 16)
    return random.Random(seed)


def get_questions_for_dimension(dimension: str, session_id: str, count: int = 1) -> list[QuestionTemplate]:
    matching = [q for q in TEMPLATES if q.dimension == dimension]
    if not matching:
        return []
    rng = _make_rng(session_id)
    return rng.sample(matching, min(count, len(matching)))


def pick_question(dimension: str, session_id: str) -> QuestionTemplate | None:
    pool = [q for q in TEMPLATES if q.dimension == dimension]
    if not pool:
        return None
    rng = _make_rng(session_id)
    return rng.choice(pool)


def pick_followup(question: QuestionTemplate, session_id: str, used_followups: set[str] | None = None) -> str | None:
    pool = question.followups
    if used_followups:
        pool = [f for f in pool if f not in used_followups]
    if not pool:
        return None
    rng = _make_rng(session_id)
    return rng.choice(pool) if pool else None


def _question_by_id(question_id: str | None) -> QuestionTemplate | None:
    if not question_id:
        return None
    for question in TEMPLATES:
        if question.id == question_id:
            return question
    return None


def recommendation_from_score(score: float, confidence: float) -> Recommendation:
    if confidence < 0.4:
        return Recommendation.BORDERLINE
    if score >= 8.0:
        return Recommendation.STRONG_PROCEED
    if score >= 6.5:
        return Recommendation.PROCEED
    if score >= 4.5:
        return Recommendation.BORDERLINE
    return Recommendation.DO_NOT_PROCEED