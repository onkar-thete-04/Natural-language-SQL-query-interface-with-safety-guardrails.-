from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AlignmentResult:
    back_translated_question: str
    alignment_score: float
    method: str
    judge_rationale: str | None
    aligned: bool
    low_confidence: bool
