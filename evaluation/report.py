from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationReport:
    case_results: list
    guardrail_results: list
