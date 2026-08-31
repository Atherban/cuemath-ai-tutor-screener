from __future__ import annotations

from app.services.interview.state import InterviewAction, InterviewStage


async def test_get_opening(engine, session):
    text, action = await engine.get_opening(session)
    assert "welcome" in text.lower()
    assert action == InterviewAction.ASK_PRIMARY.value
    assert session.current_stage == InterviewStage.INTRO.value


async def test_intro_answer_moves_to_simplification(engine, session, fake_ai):
    """After the intro answer, the AI generates a personalised simplification question."""
    fake_ai.enqueue("You mentioned you studied engineering. Can you explain what a quadratic equation is to a 7-year-old?")
    await engine.get_opening(session)
    outcome = await engine.process_candidate_turn(
        session, "I studied engineering and I love working with kids."
    )
    assert outcome["action"] == InterviewAction.ASK_PRIMARY.value
    assert outcome["stage"] == InterviewStage.SIMPLIFICATION.value
    assert "7-year-old" in outcome["text"].lower() or "quadratic" in outcome["text"].lower()
    assert outcome["is_final"] is False


async def test_walks_through_all_stages(engine, session, fake_ai):
    """The interview moves through all 5 stages and ends with CLOSING."""
    await engine.get_opening(session)
    # Each stage generates exactly one AI question; enqueue the responses.
    fake_ai.enqueue("Explain X to a 7-year-old.")  # SIMPLIFICATION
    fake_ai.enqueue("But why does it work like that?")  # ROLEPLAY
    fake_ai.enqueue("How do you check if a student really gets it?")  # METHODOLOGY
    fake_ai.enqueue("What if a student is distracted?")  # SCENARIO

    answers = [
        "I studied engineering.",
        "I'd use a pizza analogy.",
        "Because that's how numbers work.",
        "I'd ask them to explain it back.",
        "I'd talk to them privately.",
    ]
    is_final = False
    for answer in answers:
        outcome = await engine.process_candidate_turn(session, answer)
        if outcome["is_final"]:
            is_final = True
            assert outcome["stage"] == InterviewStage.CLOSING.value
            break
    assert is_final
    assert len(session.topics_covered) >= 4  # simplification, roleplay, methodology, scenario


async def test_time_up_signal_ends_interview(engine, session):
    await engine.get_opening(session)
    outcome = await engine.process_candidate_turn(
        session, "I studied engineering. TIME_IS_UP_SIGNAL"
    )
    assert outcome["is_final"] is True
    assert outcome["action"] == InterviewAction.END_INTERVIEW.value


async def test_abusive_answer_terminates(engine, session, fake_ai):
    await engine.get_opening(session)
    outcome = await engine.process_candidate_turn(
        session, "I just wanted to kick the shit out of students"
    )
    assert outcome["is_final"] is True
    assert session.fail_reason == "CANDIDATE_NON_COOPERATION"


async def test_transcript_history_recorded(engine, session, fake_ai):
    fake_ai.enqueue("Explain X to a 7-year-old.")
    await engine.get_opening(session)
    await engine.process_candidate_turn(session, "I studied engineering.")
    roles = [e.role for e in session.conversation_history]
    assert "candidate" in roles
    assert "interviewer" in roles


async def test_should_end_after_max_questions(engine, session):
    session.turn_count = engine._max_total_questions
    assert engine.should_end(session) is True


async def test_ai_multi_question_output_truncated(engine, session, fake_ai):
    """If the AI emits two questions, only the first is asked (no drilling)."""
    from app.services.interview.engine import _single_question

    multi = "Can you explain that to a 7-year-old? And also how would you check they understood it?"
    assert _single_question(multi) == "Can you explain that to a 7-year-old?"
    assert "And also" not in _single_question(multi)


async def test_skip_marker_advances_stage(engine, session, fake_ai):
    """A skipped question records '(no response)' and advances the stage."""
    fake_ai.enqueue("Explain X to a 7-year-old.")  # SIMPLIFICATION
    fake_ai.enqueue("But why does it work?")  # ROLEPLAY
    fake_ai.enqueue("How do you check understanding?")  # METHODOLOGY
    fake_ai.enqueue("What if a student is distracted?")  # SCENARIO

    await engine.get_opening(session)
    from app.services.interview.prompts import SKIP_MARKER

    outcome = await engine.process_candidate_turn(session, SKIP_MARKER)
    assert outcome["stage"] == InterviewStage.SIMPLIFICATION.value
    assert outcome["is_final"] is False
    # The skipped answer was recorded as a neutral turn.
    assert any(t.text == "(no response)" for t in session.conversation_history)