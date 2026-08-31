from __future__ import annotations

import enum


class InterviewStage(str, enum.Enum):
    INTRO = "INTRO"
    SIMPLIFICATION = "SIMPLIFICATION"
    ROLEPLAY = "ROLEPLAY"
    METHODOLOGY = "METHODOLOGY"
    SCENARIO = "SCENARIO"
    CLOSING = "CLOSING"
    ASSESSMENT = "ASSESSMENT"


class InterviewAction(str, enum.Enum):
    ASK_PRIMARY = "ASK_PRIMARY"
    END_INTERVIEW = "END_INTERVIEW"


# Stage order defines the natural progression of the interview.
STAGE_ORDER: list[InterviewStage] = [
    InterviewStage.INTRO,
    InterviewStage.SIMPLIFICATION,
    InterviewStage.ROLEPLAY,
    InterviewStage.METHODOLOGY,
    InterviewStage.SCENARIO,
    InterviewStage.CLOSING,
    InterviewStage.ASSESSMENT,
]

# Which tutoring dimension each stage is primarily probing.
STAGE_DIMENSION: dict[InterviewStage, str] = {
    InterviewStage.INTRO: "fluency",
    InterviewStage.SIMPLIFICATION: "simplicity",
    InterviewStage.ROLEPLAY: "patience",
    InterviewStage.METHODOLOGY: "clarity",
    InterviewStage.SCENARIO: "warmth",
}

# All stages except CLOSING/ASSESSMENT must be covered before the interview
# can close naturally.
REQUIRED_COVERAGE_STAGES: list[InterviewStage] = [
    InterviewStage.SIMPLIFICATION,
    InterviewStage.ROLEPLAY,
    InterviewStage.METHODOLOGY,
    InterviewStage.SCENARIO,
]


def next_stage(stage: InterviewStage) -> InterviewStage | None:
    try:
        index = STAGE_ORDER.index(stage)
    except ValueError:
        return None
    if index + 1 >= len(STAGE_ORDER):
        return None
    return STAGE_ORDER[index + 1]


def dimension_for_stage(stage: InterviewStage) -> str | None:
    return STAGE_DIMENSION.get(stage)


def remaining_required_stages(completed: list[InterviewStage]) -> list[InterviewStage]:
    return [s for s in REQUIRED_COVERAGE_STAGES if s not in completed]