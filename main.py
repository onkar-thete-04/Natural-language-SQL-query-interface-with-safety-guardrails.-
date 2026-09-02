from __future__ import annotations

import sys


def _print_result(result) -> None:
    settings = None
    print(f"Question: {result.question}")
    print("-" * 60)

    print(f"\nGenerated SQL:")
    print("=" * 60)
    print(result.generated_sql.sql)
    print("=" * 60)
    print(f"\nExplanation: {result.generated_sql.explanation}")
    print(f"Confidence:  {result.generated_sql.confidence:.2f}")
    print(f"Tables:      {result.generated_sql.tables}")
    print(f"Columns:     {result.generated_sql.columns}")

    if result.alignment is not None:
        print("\nBack-translation alignment:")
        print(f"    Back-translated: {result.alignment.back_translated_question}")
        print(f"    Alignment: {result.alignment.alignment_score:.2f} ({result.alignment.method})")
        if result.alignment.low_confidence:
            print("    WARNING: low alignment -- SQL may not answer the original question")

    if result.second_sql is not None:
        print("\nMulti-query second approach:")
        print(f"    {result.second_sql.sql}")
    else:
        print("\nMulti-query: simple question -- second approach skipped")

    print("\nGuardrail:")
    if result.guardrail.passed:
        print("    All guardrail checks passed.")
    else:
        for v in result.guardrail.violations:
            print(f"    [{v.rule}] {v.reason}")
    if result.guarded_sql != result.generated_sql.sql:
        print("    SQL rewritten by row-limit rule:")
        print(f"    {result.guarded_sql}")

    print("\nExecution results:")
    print(f"    Row count:      {result.execution.row_count}")
    print(f"    Execution time: {result.execution.execution_time_ms:.2f} ms")
    print(f"    Truncated:      {result.execution.truncated}")
    print(f"    Columns:        {result.execution.columns}")
    print("    Preview (first 5 rows):")
    for i, row in enumerate(result.execution.data[:5]):
        print(f"      {i}: {row}")

    if result.sanity is not None:
        print(f"\nSanity checks: {result.sanity.passed}/{result.sanity.checks_run} passed")
        for a in result.sanity.anomalies:
            print(f"    [{a.severity}] {a.check}: {a.message}")

    if result.agreement is not None:
        if result.agreement.agreed:
            print("\nMulti-query comparison: approaches AGREE")
        else:
            print("\nMulti-query comparison: approaches DIVERGE")
            print(f"    {result.agreement.divergence_detail}")

    print("\n" + "=" * 60)
    print(f"CONFIDENCE: {result.confidence_report.overall:.1f} / 100")
    print("=" * 60)
    for s in result.confidence_report.signals:
        bar = "#" * int(round(s.score * 20))
        print(f"  {s.name:28s} {s.score:5.2f}  {bar}")
    if result.confidence_report.flags:
        print("\n  Flags:")
        for f in result.confidence_report.flags:
            print(f"    - {f}")


def run_pipeline(question: str) -> None:
    from shared.config import Settings
    from shared.errors import (
        SchemaIntrospectionError,
        LLMClientError,
        SQLValidationError,
        GuardrailError,
        ExecutionError,
    )
    from pipeline.service import PipelineService

    settings = Settings()
    print(f"DB: {settings.db_url}")
    print(f"Model: {settings.sql_gen_model}")

    service = PipelineService(settings)
    try:
        result = service.run(question)
    except (LLMClientError, SQLValidationError) as exc:
        print(f"SQL generation failed: {exc}")
        sys.exit(1)
    except GuardrailError as exc:
        print(f"QUERY BLOCKED by guardrail: {exc}")
        sys.exit(1)
    except ExecutionError as exc:
        print(f"Execution failed: {exc}")
        sys.exit(1)
    except SchemaIntrospectionError as exc:
        print(f"ERROR: {exc}")
        print("Make sure PostgreSQL is running: docker-compose up -d")
        sys.exit(1)

    _print_result(result)

    if settings.block_on_low_confidence and result.confidence_report.overall < settings.min_confidence_score:
        print(f"\n  BLOCKED: confidence {result.confidence_report.overall:.1f} below floor {settings.min_confidence_score}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python main.py "<natural language question>"')
        sys.exit(1)
    question = " ".join(sys.argv[1:])
    run_pipeline(question)
