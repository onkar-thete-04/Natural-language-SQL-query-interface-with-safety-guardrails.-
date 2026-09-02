from unittest import mock

from evaluation.runner import CaseResult, EvaluationRunner


def _settings(tmp_path):
    return type("S", (), {
        "golden_dataset_path": "g.yaml",
        "guardrail_cases_path": "gc.yaml",
        "eval_report_path": str(tmp_path / "report.json"),
        "readonly_db_url": "postgresql://readonly_user:readonly_pass@localhost:5432/pagila",
        "enforce_row_limit": 1000,
        "min_confidence_score": 60.0,
        "db_url": "postgresql://postgres:123456@localhost:5432/pagila",
    })()


@mock.patch("evaluation.runner.classify_hallucination")
@mock.patch("evaluation.runner.evaluate_execution")
@mock.patch("evaluation.runner.evaluate_sql")
@mock.patch("evaluation.runner.OfflinePipelineService")
@mock.patch("evaluation.runner.load_cases")
@mock.patch("evaluation.runner.load_guardrail_cases")
@mock.patch("evaluation.runner.EvaluationReport")
def test_runner_iterates_cases_offline(mock_report, load_gc, load_cases, pipeline_cls, eval_sql, eval_exec, classify, tmp_path):
    from evaluation.dataset import GoldenCase
    load_cases.return_value = [GoldenCase("c1", "simple_lookup", "q1", "SELECT 1;", 1, "")]
    load_gc.return_value = []

    service = mock.MagicMock()
    service.run.return_value = mock.MagicMock()
    pipeline_cls.return_value = service

    runner = EvaluationRunner(_settings(tmp_path), offline=True)
    runner.run()

    assert service.run.call_count == 1
    assert mock_report.called


@mock.patch("evaluation.runner.create_engine")
@mock.patch("evaluation.runner.evaluate_guardrail")
@mock.patch("evaluation.runner.load_cases")
@mock.patch("evaluation.runner.load_guardrail_cases")
@mock.patch("evaluation.runner.EvaluationReport")
def test_runner_runs_guardrail_cases(mock_report, load_gc, load_cases, eval_g, create_engine, tmp_path):
    load_cases.return_value = []
    load_gc.return_value = [{"id": "g1", "sql": "DROP TABLE film;"}]
    eval_g.return_value = mock.MagicMock(blocked=True, rules=["block_ddl"])

    runner = EvaluationRunner(_settings(tmp_path), offline=True)
    runner.run()

    assert eval_g.call_count == 1
    assert create_engine.called
