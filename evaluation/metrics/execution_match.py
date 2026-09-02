from __future__ import annotations

from dataclasses import dataclass

from evaluation.dataset import GoldenCase
from executor.runner import execute
from multi_query.comparator import compare
from sandbox.engine import create_readonly_engine, read_only_session


@dataclass(frozen=True)
class ExecutionMatchResult:
    case_id: str
    applicable: bool
    matched: bool | None
    detail: str


def evaluate(case: GoldenCase, result, readonly_db_url: str, row_limit: int) -> ExecutionMatchResult:
    if case.category == "unanswerable":
        matched = result.execution.row_count == 0
        return ExecutionMatchResult(
            case.id, True, matched,
            "" if matched else "expected empty result but generated SQL returned rows",
        )

    golds = case.gold_sql if isinstance(case.gold_sql, list) else [case.gold_sql]

    engine = create_readonly_engine(readonly_db_url)
    with read_only_session(engine) as conn:
        for gold in golds:
            gold_exec = execute(gold, conn, row_limit=row_limit)
            agreement = compare(result.execution, gold_exec)
            if agreement.agreed:
                return ExecutionMatchResult(case.id, True, True, "")
    return ExecutionMatchResult(case.id, True, False, "generated result diverges from gold SQL result")
