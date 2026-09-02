from __future__ import annotations

from dataclasses import dataclass

from eval.cases import EvalCase, load_cases


@dataclass(frozen=True)
class EvalCaseResult:
    case_id: str
    passed: bool
    detail: str


def run_case(case: EvalCase, service, readonly_db_url: str, enforce_row_limit: int) -> EvalCaseResult:
    from executor.runner import execute
    from multi_query.comparator import compare
    from sandbox.engine import create_readonly_engine, read_only_session

    current = service.run(case.question)
    readonly_engine = create_readonly_engine(readonly_db_url)

    with read_only_session(readonly_engine) as conn:
        if case.gold_sql:
            gold = execute(case.gold_sql, conn, row_limit=enforce_row_limit)
            agreement = compare(current.execution, gold)
            if agreement.agreed:
                return EvalCaseResult(case.id, True, "generated SQL matches gold SQL result")
            return EvalCaseResult(case.id, False, agreement.divergence_detail or "result sets diverge from gold")

        recorded = execute(case.generated_sql, conn, row_limit=enforce_row_limit)
        agreement = compare(current.execution, recorded)
        if agreement.agreed:
            return EvalCaseResult(case.id, False, "still reproduces the recorded-incorrect result")
        return EvalCaseResult(case.id, True, "no longer reproduces the recorded-incorrect result")


def run_all(cases: list[EvalCase], service, readonly_db_url: str, enforce_row_limit: int) -> list[EvalCaseResult]:
    return [run_case(c, service, readonly_db_url, enforce_row_limit) for c in cases]


def main() -> int:
    import sys
    from shared.config import Settings
    from pipeline.service import PipelineService

    settings = Settings()
    service = PipelineService(settings)
    cases = load_cases(settings.eval_test_cases_path)
    if not cases:
        print("No eval cases found.")
        return 0

    results = run_all(cases, service, settings.readonly_db_url, settings.enforce_row_limit)
    failed = 0
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"[{status}] {r.case_id}: {r.detail}")
        if not r.passed:
            failed += 1
    print(f"\n{len(results) - failed}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
