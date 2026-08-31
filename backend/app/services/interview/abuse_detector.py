from __future__ import annotations

import re

# Deterministic, rule-based detection of abusive / non-cooperative candidate
# answers. This is the FIRST line of defence: it runs before the AI is
# consulted, so a clearly abusive answer always terminates the interview even
# if the LLM fails to follow the prompt-level instructions.

VIOLENT_VERBS = [
    "kick", "hit", "punch", "slap", "smack", "whack", "beat", "bash",
    "kill", "murder", "hurt", "harm", "strangle", "choke", "stab", "shoot",
    "threaten", "attack",
]

STUDENT_WORDS = [
    "student", "students", "kid", "kids", "child", "children", "learner",
    "learners", "pupil", "pupils", "brat", "brats",
]

STRONG_PROFANITY = [
    "fuck", "shit", "bitch", "asshole", "bastard", "cunt", "motherfucker",
    "dickhead", "piss off", "fuck off", "screw you", "go to hell",
]

HOSTILE_DISMISSAL = [
    "this is stupid", "these questions are stupid", "waste of time",
    "wasting my time", "not answering", "i won't answer", "i wont answer",
    "i'm not answering", "i am not answering", "shut up", "i quit",
    "i'm done", "i am done", "screw this", "rubbish", "nonsense",
    "pointless", "useless interview", "i don't care", "i dont care",
    "get lost", "not doing this", "i refuse",
]

_CLOSE = (
    "I think we have everything we need for today. Thank you for your time."
)


def detect_abuse(text: str) -> str | None:
    """Return a human-readable failure reason if the answer is abusive.

    Returns None when the answer seems cooperative. Detection is intentionally
    conservative to avoid flagging ordinary speech.
    """
    if not text:
        return None
    lower = text.lower()

    # 1. Violence / threat directed at students — the most serious case.
    if _contains_violence_against_students(lower):
        return "threatening language directed at students"

    # 2. Strong profanity.
    for word in STRONG_PROFANITY:
        if re.search(rf"\b{re.escape(word)}\w*", lower):
            return "profanity / offensive language"

    # 3. Hostile dismissal / refusal to engage.
    for phrase in HOSTILE_DISMISSAL:
        if phrase in lower:
            return "refusal to engage with the interview"

    return None


def _contains_violence_against_students(lower: str) -> bool:
    # A violent verb and a student reference must both appear. Requiring both
    # avoids flagging e.g. "kick a football" or "hit the target".
    has_verb = any(re.search(rf"\b{re.escape(v)}", lower) for v in VIOLENT_VERBS)
    has_student = any(s in lower for s in STUDENT_WORDS)
    if not (has_verb and has_student):
        return False
    # Violence verbs must be near a student word (same or adjacent clause).
    for v in VIOLENT_VERBS:
        for m in re.finditer(rf"\b{re.escape(v)}\w*", lower):
            span = lower[max(0, m.start() - 40) : m.end() + 40]
            if any(s in span for s in STUDENT_WORDS):
                return True
    return False


def non_cooperation_closing() -> str:
    """Firm, polite closing used when the interview is terminated for abuse."""
    return _CLOSE
