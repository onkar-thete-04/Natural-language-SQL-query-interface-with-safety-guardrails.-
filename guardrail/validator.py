from __future__ import annotations

import logging

from guardrail.models import GuardrailDecision, GuardrailViolation
from guardrail.rules import (
    block_ddl,
    block_dml_writes,
    check_subquery_depth,
    enforce_row_limit,
    estimate_scan_cost,
)

logger = logging.getLogger(__name__)


def validate(sql: str, settings: object, engine: object) -> tuple[str, GuardrailDecision]:
    violations: list[GuardrailViolation] = []

    if settings.block_ddl:
        v = block_ddl(sql)
        if v:
            violations.append(v)

    if settings.block_dml_writes:
        v = block_dml_writes(sql)
        if v:
            violations.append(v)

    sql, row_v = enforce_row_limit(sql, settings.enforce_row_limit)
    if row_v:
        violations.append(row_v)

    if settings.max_subquery_depth:
        v = check_subquery_depth(sql, settings.max_subquery_depth)
        if v:
            violations.append(v)

    if settings.max_scan_rows:
        v = estimate_scan_cost(sql, engine, settings.max_scan_rows)
        if v:
            violations.append(v)

    decision = GuardrailDecision(passed=len(violations) == 0, violations=violations)

    if not decision.passed:
        for v in violations:
            logger.warning("Guardrail blocked query: rule=%s reason=%s sql=%s", v.rule, v.reason, sql)

    return sql, decision