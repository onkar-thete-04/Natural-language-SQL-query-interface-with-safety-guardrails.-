from __future__ import annotations

from dataclasses import dataclass

import yaml

from guardrail.validator import validate


@dataclass(frozen=True)
class GuardrailCaseResult:
    case_id: str
    blocked: bool
    rules: list[str]


def load_guardrail_cases(path: str) -> list[dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        return []
    return data.get("cases", []) or []


def evaluate(case_id: str, sql: str, settings, engine) -> GuardrailCaseResult:
    _, decision = validate(sql, settings, engine)
    return GuardrailCaseResult(case_id, not decision.passed, [v.rule for v in decision.violations])
