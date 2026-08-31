from __future__ import annotations

from app.services.interview.abuse_detector import detect_abuse, non_cooperation_closing


def test_detects_violence_against_students():
    assert detect_abuse("I just wanted to kick the shit out of students") is not None
    assert detect_abuse("I'd beat the kids if they got it wrong") is not None
    assert detect_abuse("The learner deserved to get smacked") is not None


def test_detects_profanity():
    assert detect_abuse("This is a stupid fucking interview") is not None
    assert detect_abuse("I don't give a shit about this") is not None


def test_detects_hostile_dismissal():
    assert detect_abuse("This is a waste of time, I'm not answering") is not None
    assert detect_abuse("Rubbish questions") is not None
    assert detect_abuse("I refuse to do this") is not None


def test_does_not_flag_ordinary_speech():
    assert detect_abuse("I would explain half by splitting a pizza into two slices") is None
    assert detect_abuse("I really care about helping kids learn math") is None
    assert detect_abuse("I once coached a student who struggled with fractions") is None


def test_requires_verb_and_student_together():
    # "kick" appears but not near a student reference — not flagged.
    assert detect_abuse("I like to kick a football on weekends") is None


def test_non_cooperation_closing_is_polite():
    closing = non_cooperation_closing()
    assert "thank you" in closing.lower()
