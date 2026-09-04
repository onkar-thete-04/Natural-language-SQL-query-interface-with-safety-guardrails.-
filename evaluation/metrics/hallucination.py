from __future__ import annotations

from dataclasses import dataclass

from evaluation.metrics.execution_match import ExecutionMatchResult


@dataclass(frozen=True)
class HallucinationResult:
    case_id: str
    is_bad: bool
    flagged: bool


def is_flagged(result, min_confidence_score: float) -> bool:
    if result.alignment is not None and not result.alignment.aligned:
        return True
    if result.sanity is not None and result.sanity.anomalies:
        return True
    if result.confidence_report.overall < min_confidence_score:
        return True
    if result.clarification is not None:
        return True
    return False


def classify(case_id: str, result, execution: ExecutionMatchResult, min_confidence_score: float) -> HallucinationResult:
    is_bad = execution.applicable and execution.matched is False
    return HallucinationResult(case_id, is_bad, is_flagged(result, min_confidence_score))


def compute_rate(results: list[HallucinationResult]) -> dict:
    bad = [r for r in results if r.is_bad]
    flagged = [r for r in results if r.flagged]
    flagged_bad = [r for r in bad if r.flagged]
    return {
        "recall": (len(flagged_bad) / len(bad)) if bad else None,
        "precision": (len(flagged_bad) / len(flagged)) if flagged else None,
    }
