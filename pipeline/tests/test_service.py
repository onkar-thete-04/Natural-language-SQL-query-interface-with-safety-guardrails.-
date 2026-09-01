from __future__ import annotations

import contextlib
from unittest.mock import MagicMock

import pytest

from pipeline.service import PipelineService


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    from shared.config import Settings
    return Settings()


def _patch_collaborators(monkeypatch):
    from guardrail.models import GuardrailDecision
    from sql_generator.models import SQLResult

    fakes = {
        "schema": MagicMock(),
        "sql_result": SQLResult(
            sql="SELECT 1;", explanation="ex", confidence=0.9,
            tables=["payment"], columns=["amount"],
        ),
        "decision": GuardrailDecision(passed=True, violations=[]),
    }

    import schema_engine.introspector
    introspector = MagicMock()
    introspector.introspect.return_value = fakes["schema"]
    monkeypatch.setattr(schema_engine.introspector, "SchemaIntrospector", lambda url: introspector)

    import schema_engine.sampler
    monkeypatch.setattr(
        schema_engine.sampler, "enrich_schema_with_samples",
        lambda schema, engine, limit: schema,
    )

    import relevance_filter.embedder
    monkeypatch.setattr(relevance_filter.embedder, "SchemaEmbedder", lambda model: MagicMock())

    import relevance_filter.scorer
    monkeypatch.setattr(
        relevance_filter.scorer, "RelevanceScorer",
        lambda embedder, schema, threshold: MagicMock(score_tables=lambda q: ["payment"]),
    )

    import ambiguity_resolver.detector
    monkeypatch.setattr(
        ambiguity_resolver.detector, "AmbiguityDetector",
        lambda embedder, schema: MagicMock(detect=lambda q: None),
    )

    import prompt_builder.constructor
    monkeypatch.setattr(
        prompt_builder.constructor, "PromptConstructor",
        lambda schema, loader, settings: MagicMock(build=lambda **kw: "prompt"),
    )

    import few_shot_loader
    monkeypatch.setattr(few_shot_loader, "FewShotLoader", lambda: MagicMock())

    import sql_generator.generator
    generator = MagicMock()
    generator.generate.return_value = fakes["sql_result"]
    monkeypatch.setattr(sql_generator.generator, "SQLGenerator", lambda **kw: generator)

    import back_translation.translator
    monkeypatch.setattr(back_translation.translator, "back_translate", lambda sql, client, settings: "q")

    import back_translation.aligner
    alignment = MagicMock()
    monkeypatch.setattr(back_translation.aligner, "align", lambda q, bt, e, c, s: alignment)

    import multi_query.complexity
    monkeypatch.setattr(multi_query.complexity, "is_complex", lambda q, r: False)

    import guardrail.validator
    monkeypatch.setattr(
        guardrail.validator, "validate",
        lambda sql, settings, engine: (sql, fakes["decision"]),
    )

    import sandbox.engine
    monkeypatch.setattr(sandbox.engine, "create_readonly_engine", lambda url: MagicMock())
    monkeypatch.setattr(sandbox.engine, "read_only_session", lambda engine: contextlib.nullcontext())

    import executor.runner
    execution = MagicMock()
    monkeypatch.setattr(executor.runner, "execute", lambda sql, conn, row_limit: execution)

    import sanity_check.checks
    monkeypatch.setattr(sanity_check.checks, "run_checks", lambda *a, **kw: None)

    import sanity_check.empty_result
    monkeypatch.setattr(sanity_check.empty_result, "check_empty_result", lambda *a, **kw: None)

    import confidence.scorer
    monkeypatch.setattr(confidence.scorer, "compute_schema_coverage", lambda *a: (1.0, []))
    monkeypatch.setattr(confidence.scorer, "compute_confidence", lambda **kw: MagicMock(overall=92.6))

    return fakes


def test_run_returns_pipeline_result(settings, monkeypatch):
    from pipeline.models import PipelineResult
    _patch_collaborators(monkeypatch)
    service = PipelineService(settings)
    result = service.run("which store generated the most revenue")
    assert isinstance(result, PipelineResult)
    assert result.question == "which store generated the most revenue"
    assert result.generated_sql.sql == "SELECT 1;"
    assert result.guarded_sql == "SELECT 1;"


def test_run_guardrail_block_raises(settings, monkeypatch):
    from guardrail.models import GuardrailDecision, GuardrailViolation
    from shared.errors import GuardrailError
    fakes = _patch_collaborators(monkeypatch)

    import guardrail.validator
    blocked = GuardrailDecision(
        passed=False,
        violations=[GuardrailViolation(rule="block_dml_writes", reason="no writes")],
    )
    monkeypatch.setattr(guardrail.validator, "validate", lambda sql, settings, engine: (sql, blocked))

    service = PipelineService(settings)
    with pytest.raises(GuardrailError):
        service.run("delete all rows")
