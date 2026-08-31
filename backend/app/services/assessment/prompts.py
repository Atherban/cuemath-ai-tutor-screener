from __future__ import annotations

import json
from typing import Any

from app.services.assessment.rubric import DIMENSIONS

# Map interview stages to the soft-skill dimension each question probes.
STAGE_DIMENSION: dict[str, str] = {
    "INTRO": "fluency",
    "SIMPLIFICATION": "simplicity",
    "ROLEPLAY": "patience",
    "METHODOLOGY": "clarity",
    "SCENARIO": "warmth",
}


def build_evaluation_prompt(
    answers_by_stage: list[tuple[str, str, str]],
) -> str:
    """Build the prompt for the AI evaluator.

    Each interview question was independent and probed ONE parameter. The
    evaluator scores each parameter against the specific answer the candidate
    gave for that stage, so scores are evidence-linked to the right question.
    """
    dimension_specs = []
    for key, dim in DIMENSIONS.items():
        dimension_specs.append(f"- {dim.label} ({key}): {dim.description}")

    qa_lines = []
    for stage, question, answer in answers_by_stage:
        qa_lines.append(
            f"[{STAGE_DIMENSION.get(stage, stage)}] Q: {question}\n"
            f"   A: {answer}"
        )

    return f"""\
You are a warm, fair evaluator scoring a first-round tutor screening interview for \
Cuemath. The interview asked exactly one independent question per soft-skill \
parameter. Score tutoring soft skills ONLY, and be GENEROUS: most engaged, \
reasonable candidates should score in the 7-9 range. Use the full 0-10 scale — \
reserve 0-3 for clearly unhelpful, incoherent, or disengaged answers.

FAIRNESS: ignore accent, region, gender, ethnicity, appearance, background. \
"Fluency" = comprehensibility + vocabulary + sentence construction, never \
native-speaker status. Assess behaviour, never personality stereotypes.

EVIDENCE: back each score with a short quote from the matching answer below and \
a one-sentence reason. If a parameter has no supporting quote, score it lower \
(4-6) with evidence_status="PARTIAL" — do NOT score 0 for a merely short or \
imperfect answer. NEVER invent quotes.

Each parameter is scored against the candidate's answer to THAT parameter's \
question — do not use another answer as evidence.

Dimensions to score:
{chr(10).join(dimension_specs)}

QUESTION / ANSWER PAIRS (each maps to one parameter):
{chr(10).join(qa_lines) if qa_lines else '(no candidate responses)'}

Return STRICT JSON ONLY, shape:
{{
  "dimensions": {{
    "clarity": {{"score": 0, "confidence": 0.0, "summary": "one short sentence", "strengths": ["..."], "concerns": ["..."], "evidence": [{{"quote": "exact words", "reason": "why it supports the score"}}], "evidence_status": "SUFFICIENT"}},
    "simplicity": {{...}},
    "patience": {{...}},
    "warmth": {{...}},
    "fluency": {{...}}
  }},
  "key_strengths": [],
  "key_concerns": [],
  "overall_score": 0.0,
  "confidence": 0.0,
  "summary": "one short sentence"
}}

Rules:
- score: number 0-10; confidence: 0-1; evidence_status: SUFFICIENT|PARTIAL|INSUFFICIENT.
- MAX 2 evidence items per dimension, MAX 1 sentence per summary.
- Output the JSON object only — no other text, no markdown fences.
"""


def parse_evaluator_json(raw: str) -> dict[str, Any] | None:
    """Safely parse the evaluator's JSON output, tolerating code fences."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to extract the first {...} block.
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return None
        return None
