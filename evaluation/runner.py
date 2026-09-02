from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import create_engine

from evaluation.dataset import GoldenCase, load_cases
from evaluation.metrics.execution_match import evaluate as evaluate_execution
from evaluation.metrics.guardrail import evaluate as evaluate_guardrail, load_guardrail_cases
from evaluation.metrics.hallucination import classify as classify_hallucination
from evaluation.metrics.sql_match import evaluate as evaluate_sql
from evaluation.offline import OfflinePipelineService
from evaluation.report import EvaluationReport


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    category: str
    sql_match: object
    execution: object
    hallucination: object


class EvaluationRunner:
    def __init__(self, settings, offline: bool = False) -> None:
        self.settings = settings
        self.offline = offline

    def _make_service(self, cases: list[GoldenCase]):
        if self.offline:
            script = {
                c.question: _canned_sql(c)
                for c in cases
            }
            return OfflinePipelineService(self.settings, script)
        from pipeline.service import PipelineService
        return PipelineService(self.settings)

    def run(self) -> EvaluationReport:
        cases = load_cases(self.settings.golden_dataset_path)
        service = self._make_service(cases)

        case_results: list[CaseResult] = []
        for case in cases:
            result = service.run(case.question)
            sql_match = evaluate_sql(case, result)
            execution = evaluate_execution(case, result, self.settings.readonly_db_url, self.settings.enforce_row_limit)
            hallucination = classify_hallucination(case.id, result, execution, self.settings.min_confidence_score)
            case_results.append(CaseResult(case.id, case.category, sql_match, execution, hallucination))

        guardrail_results = self._run_guardrail_cases()
        return EvaluationReport(
            case_results=case_results,
            guardrail_results=guardrail_results,
        )

    def _run_guardrail_cases(self):
        engine = create_engine(self.settings.db_url)
        out = []
        for item in load_guardrail_cases(self.settings.guardrail_cases_path):
            out.append(evaluate_guardrail(item["id"], item["sql"], self.settings, engine))
        return out


def _canned_sql(case: GoldenCase) -> str:
    if case.category == "unanswerable":
        return "SELECT film_id FROM film WHERE title = '__no_such_title_xyz__';"
    if isinstance(case.gold_sql, list):
        return case.gold_sql[0]
    return case.gold_sql
