from __future__ import annotations

import random

# Emitted by the model (after a polite closing statement) when it decides the
# candidate is not cooperating and the interview should end early.
EARLY_TERMINATION_MARKER = "__EARLY_TERMINATION__"

# Marker the candidate can type to end the interview immediately.
TIME_UP_SIGNAL = "TIME_IS_UP_SIGNAL"

# Marker the frontend sends when the per-question timer expires with no
# answer. The engine records "(no response)" and advances to the next stage.
SKIP_MARKER = "__SKIP_QUESTION__"

_ABUSE_HANDLING = """\
If the candidate's latest response is aggressive, abusive, insulting, hostile, \
or a clearly disengaged / useless answer (e.g. cursing, threats, "this is \
stupid", gibberish, or refusing to participate), do NOT keep asking questions. \
Politely conclude by saying something like "I think we have enough for today — \
thank you for your time." Then, on a brand-new line, output exactly {marker}.
"""

# Pools of concepts, ages, and scenarios to make each interview feel fresh.
_CONCEPTS = [
    "fractions", "decimals", "percentages", "area of a rectangle",
    "negative numbers", "long multiplication", "long division",
    "place value", "symmetry", "telling time", "money word problems",
    "basic probability", "measuring length", "reading a bar chart",
    "comparing fractions", "rounding numbers", "averages", "ratios",
]
_AGES = [6, 7, 8, 9, 10]
# A random flavour injected into every question so the model never collapses
# the stages into the same generic question across sessions.
_FLAVOURS = [
    "using a real-world example the child would recognise",
    "with a creative analogy from everyday life",
    "step by step, checking understanding as you go",
    "using a simple drawing or visual",
    "by connecting it to something the child already enjoys",
    "keeping it playful and encouraging",
]
_ROLEPLAY_SCENARIOS = [
    "a student who has just said they are confused and are about to give up",
    "a student who stares at their worksheet silently and says 'I don't get it'",
    "a student who keeps making the same mistake and looks frustrated",
    "a student who says 'this is too hard' and pushes their paper away",
    "a student who starts crying because they cannot solve a problem",
    "a student who says 'I'm just not good at maths' and stops trying",
]
_SCENARIO_SCENARIOS = [
    "A child who is normally cheerful comes in looking upset and says they "
    "hate maths. What do you say or do?",
    "A parent tells you their child is 'just not good at maths' and asks you "
    "to lower expectations. How do you respond?",
    "A student answers a question confidently but gets it completely wrong. "
    "How do you correct them without discouraging them?",
    "A student says 'I already know this' and refuses to listen to your "
    "explanation. How do you handle it?",
    "A student who is usually quiet finally raises their hand but gives the "
    "wrong answer. How do you respond?",
    "A student finishes every problem instantly but cannot explain their "
    "reasoning. How do you deepen their thinking?",
]
_METHODOLOGY_SCENARIOS = [
    "how you would check whether a student truly understands a concept "
    "versus just memorising the steps",
    "what question you would ask to see if a student can apply a concept "
    "to a slightly different problem than the one you taught",
    "how you would spot the difference between a student who is stuck and "
    "one who is just not paying attention",
    "how you would design a quick five-minute activity to test whether a "
    "student can teach the concept back to you",
    "what you would do if a student can solve problems correctly but cannot "
    "explain why the method works",
]


# One independent, self-contained question per parameter. Each directive probes
# a SINGLE soft-skill dimension from the source of truth. The AI must NOT build
# on, echo, or continue the candidate's earlier answers — every question stands
# alone so each parameter is evaluated in isolation.
def _build_directives() -> dict[str, str]:
    concept = random.choice(_CONCEPTS)
    age = random.choice(_AGES)
    flavour = random.choice(_FLAVOURS)
    roleplay = random.choice(_ROLEPLAY_SCENARIOS)
    scenario = random.choice(_SCENARIO_SCENARIOS)
    method = random.choice(_METHODOLOGY_SCENARIOS)

    return {
        "INTRO": (
            "Ask the candidate ONE warm, simple question to introduce themselves — "
            "who they are, their background, and why they want to be a maths tutor. "
            "This evaluates English fluency: how clearly and comfortably they "
            "communicate."
        ),
        "SIMPLIFICATION": (
            f"Ask the candidate to explain {concept} to a {age}-year-old child, "
            f"{flavour}. This evaluates SIMPLICITY only. Do not reference their "
            f"own background or previous answers."
        ),
        "ROLEPLAY": (
            f"Present a fresh, independent scenario: {roleplay}. Ask what the "
            f"candidate would do or say in that moment, {flavour}. This evaluates "
            f"PATIENCE only. Do NOT reference any earlier answer."
        ),
        "METHODOLOGY": (
            f"Ask the candidate {method}, {flavour}. This evaluates COMMUNICATION "
            f"CLARITY only. Do NOT reference any earlier answer."
        ),
        "SCENARIO": (
            f"Present ONE fresh, specific classroom scenario: {scenario} "
            f"Handle it {flavour}. This evaluates WARMTH / EMPATHY only. Do NOT "
            f"reference any earlier answer."
        ),
        "CLOSING": (
            "Politely conclude the interview and thank the candidate for their time. "
            "Do not reveal any scores or decisions."
        ),
    }


STAGE_PROMPT = """\
You are a warm, professional recruiter conducting the first-round screening for \
a Cuemath tutor position. Cuemath tutors teach maths to young learners, so you \
are assessing tutoring soft skills: communication clarity, patience, warmth, \
the ability to simplify, and English fluency. It is NOT a test of advanced \
mathematics.

Your current task for this stage ({stage}):

{directive}

Rules you must follow:

1. Output EXACTLY ONE question. Never two, never three. One single question, \
   then stop.
2. ASK A BRAND-NEW, INDEPENDENT QUESTION. Do NOT build on, echo, reference, or \
   continue anything the candidate said earlier. Each question stands alone and \
   evaluates its own single parameter.
3. Do NOT drill down. Do not chain follow-ups. Do not repeat the candidate's \
   words back to them.
4. Be concise and conversational, like a real spoken interviewer (1-3 sentences).
5. NEVER reveal scoring, rubric, evaluation, or hiring decisions.
6. Produce ONLY the question — no labels, no commentary, no quotes.
7. Do not break character (especially in ROLEPLAY, where you are the student).
{abuse_handling}
Interview objective: {objective}
"""

OPENING_TEMPLATE = """\
Hello, welcome to the interview. I'm your interviewer today. We'll have a short \
conversation about how you'd teach maths to young learners. There are no trick \
questions, so just answer as you naturally would. Ready when you are — tell me \
about yourself and why you'd like to become a maths tutor.
"""

SILENCE_GENTLE = """\
Take your time — I'm still here. Whenever you're ready, go ahead.
"""

SILENCE_OFFER_CHANCE = """\
No pressure at all. If you'd like to take another moment to think it through, \
that's fine — or we can move on to the next question.
"""

CLOSING_TEMPLATE = """\
That's everything I wanted to cover. Thank you so much for your time today — you \
gave me some great insight into how you'd work with young learners. I really \
appreciate it, and I hope to be in touch soon. Take care!
"""


def build_objective() -> str:
    return (
        "Screen a tutor candidate for the soft skills needed to teach maths to "
        "young learners: communication clarity, patience, warmth, the ability to "
        "simplify, and English fluency. The interview asks exactly one "
        "independent question per parameter (intro/fluency, simplification/"
        "simplicity, roleplay/patience, methodology/clarity, scenario/warmth). "
        "Each answer is evaluated against its own parameter. Keep the "
        "conversation natural."
    )


def build_stage_prompt(stage: str, conversation: str) -> str:
    """Build the prompt that asks ONE independent, parameter-specific question.

    The conversation is intentionally NOT injected: each question must stand
    alone so the candidate's answer evaluates a single parameter in isolation,
    not a follow-up on an earlier answer.

    Directives are built fresh each call so every interview feels different
    (randomised concepts, ages, and scenarios).
    """
    directives = _build_directives()
    directive = directives.get(stage, directives["CLOSING"])
    return STAGE_PROMPT.format(
        stage=stage,
        directive=directive,
        objective=build_objective(),
        abuse_handling=_ABUSE_HANDLING.format(marker=EARLY_TERMINATION_MARKER),
    )