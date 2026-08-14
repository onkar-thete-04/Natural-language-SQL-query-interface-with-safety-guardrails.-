from __future__ import annotations

import sys


def run_pipeline(question: str) -> None:
    from shared.config import Settings
    from shared.errors import (
        SchemaIntrospectionError,
        LLMClientError,
        SQLValidationError,
        GuardrailError,
        ExecutionError,
    )

    print(f"Question: {question}")
    print("-" * 60)

    settings = Settings()
    print(f"DB: {settings.db_url}")
    print(f"Model: {settings.sql_gen_model}")

    print("\n[1] Introspecting schema...")
    try:
        from schema_engine.introspector import SchemaIntrospector
        introspector = SchemaIntrospector(settings.db_url)
        schema = introspector.introspect()
    except SchemaIntrospectionError as exc:
        print(f"ERROR: {exc}")
        print("Make sure PostgreSQL is running: docker-compose up -d")
        sys.exit(1)
    print(f"    Found {len(schema.tables)} tables")

    try:
        from sqlalchemy import create_engine
        engine = create_engine(settings.db_url)
        from schema_engine.sampler import enrich_schema_with_samples
        schema = enrich_schema_with_samples(schema, engine, limit=5)
        print("    Enriched with sample values")
    except Exception:
        print("    WARNING: Could not extract sample values (DB may not be running)")

    print("\n[2] Loading embedder...")
    from relevance_filter.embedder import SchemaEmbedder
    embedder = SchemaEmbedder(settings.embedding_model)
    print(f"    Model: {settings.embedding_model}")

    print("\n[3] Filtering relevant tables...")
    from relevance_filter.scorer import RelevanceScorer
    scorer = RelevanceScorer(embedder, schema, threshold=settings.similarity_threshold)
    relevant = scorer.score_tables(question)
    print(f"    Relevant tables: {relevant if relevant else 'ALL (no matches above threshold)'}")

    print("\n[4] Checking for ambiguity...")
    from ambiguity_resolver.detector import AmbiguityDetector
    detector = AmbiguityDetector(embedder, schema)
    clarification = detector.detect(question)

    clarifications_text = None
    constraint = None

    if clarification:
        print("    AMBIGUITY DETECTED:")
        for i, interp in enumerate(clarification.interpretations, 1):
            print(f"    [{i}] {interp.label}: {interp.description}")
            print(f"        Example: {interp.example_query}")
            print(f"        Constraint: {interp.constraint}")
        print("\n    Using first interpretation for this run...")
        chosen = clarification.interpretations[0]
        clarifications_text = f"User selected: {chosen.label}"
        constraint = chosen.constraint
    else:
        print("    No ambiguity detected.")

    print("\n[5] Building prompt...")
    from prompt_builder.constructor import PromptConstructor
    from few_shot_loader import FewShotLoader
    loader = FewShotLoader()
    constructor = PromptConstructor(schema, loader, settings)
    prompt = constructor.build(
        question=question, relevant_tables=relevant,
        constraint=constraint, clarifications=clarifications_text,
    )

    print(f"    Prompt length: {len(prompt)} characters")
    print("\n" + "=" * 60)
    print("ASSEMBLED PROMPT")
    print("=" * 60)
    print(prompt)
    print("=" * 60)

    print("\n[6] Calling LLM (structured output)...")
    from shared.llm_client import LLMClient
    from sql_generator.generator import SQLGenerator
    try:
        client = LLMClient(settings)
        generator = SQLGenerator(client=client, max_retries=3)
        sql_result = generator.generate(prompt)
    except (LLMClientError, SQLValidationError) as exc:
        print(f"SQL generation failed: {exc}")
        print("(Prompt was built successfully, but LLM call or validation failed)")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("GENERATED SQL")
    print("=" * 60)
    print(sql_result.sql)
    print("=" * 60)
    print(f"\nExplanation: {sql_result.explanation}")
    print(f"Confidence:  {sql_result.confidence:.2f}")
    print(f"Tables:      {sql_result.tables}")
    print(f"Columns:     {sql_result.columns}")

    print("\n[7] Back-translating SQL -> question...")
    from back_translation.translator import back_translate
    from back_translation.aligner import align
    alignment = None
    try:
        back_translated = back_translate(sql_result.sql, client, settings)
        alignment = align(question, back_translated, embedder, client, settings)
        print(f"    Back-translated: {back_translated}")
        print(f"    Alignment: {alignment.alignment_score:.2f} ({alignment.method})")
        if alignment.low_confidence:
            print("    WARNING: low alignment -- SQL may not answer the original question")
    except Exception as exc:
        print(f"    WARNING: back-translation unavailable: {exc}")

    print("\n[8] Checking multi-query complexity...")
    from multi_query.complexity import is_complex
    from multi_query.generator import generate_alternative
    second_sql_result = None
    if is_complex(question, sql_result):
        print("    Complex question -- generating second independent SQL approach...")
        try:
            second_sql_result = generate_alternative(prompt, generator)
            print(f"    Alternative SQL:\n{second_sql_result.sql}")
        except Exception as exc:
            print(f"    WARNING: alternative generation unavailable: {exc}")
            second_sql_result = None
    else:
        print("    Simple question -- skipping second approach")

    print("\n[9] Running guardrail checks...")
    from guardrail.validator import validate
    from sqlalchemy import create_engine as _ce
    guardrail_engine = _ce(settings.db_url)
    try:
        guarded_sql, decision = validate(sql_result.sql, settings, guardrail_engine)
    except Exception as exc:
        print(f"Guardrail check failed: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    if not decision.passed:
        print("    QUERY BLOCKED by guardrail:")
        for v in decision.violations:
            print(f"    [{v.rule}] {v.reason}")
        sys.exit(1)
    print("    All guardrail checks passed.")
    if guarded_sql != sql_result.sql:
        print(f"    SQL rewritten by row-limit rule:")
        print(f"    {guarded_sql}")

    print("\n[10] Opening sandbox session (read-only)...")
    from sandbox.engine import create_readonly_engine, read_only_session
    readonly_engine = create_readonly_engine(settings.readonly_db_url)

    print("\n[11] Executing query...")
    from executor.runner import execute
    try:
        with read_only_session(readonly_engine) as conn:
            result = execute(guarded_sql, conn, row_limit=settings.enforce_row_limit)
            result_b = None
            if second_sql_result is not None:
                try:
                    from guardrail.validator import validate as _validate
                    alt_sql, alt_decision = _validate(
                        second_sql_result.sql, settings, guardrail_engine
                    )
                    if alt_decision.passed:
                        result_b = execute(alt_sql, conn, row_limit=settings.enforce_row_limit)
                    else:
                        print("    Alternative SQL blocked by guardrail -- skipped")
                except Exception as exc:
                    print(f"    WARNING: alternative execution unavailable: {exc}")
    except ExecutionError as exc:
        print(f"Execution failed: {exc}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("EXECUTION RESULTS")
    print("=" * 60)
    print(f"Row count:         {result.row_count}")
    print(f"Execution time:    {result.execution_time_ms:.2f} ms")
    print(f"Truncated:         {result.truncated}")
    print(f"Columns:           {result.columns}")
    print(f"\nPreview (first 5 rows):")
    for i, row in enumerate(result.data[:5]):
        print(f"  {i}: {row}")
    print(f"\nEXPLAIN plan:\n{result.explain_plan}")
    print("=" * 60)

    print("\n[12] Running sanity checks...")
    from sanity_check.checks import run_checks
    from sanity_check.models import SanityCheckResult
    from sanity_check.empty_result import check_empty_result
    sanity = None
    try:
        with read_only_session(readonly_engine) as conn:
            sanity = run_checks(
                guarded_sql, result,
                sql_result.tables, sql_result.columns, conn, settings,
            )
            empty_anomaly = check_empty_result(
                guarded_sql, question, result,
                sql_result.tables, conn, client, settings,
            )
            if empty_anomaly is not None:
                sanity = SanityCheckResult(
                    checks_run=sanity.checks_run + 1,
                    passed=sanity.passed,
                    anomalies=sanity.anomalies + [empty_anomaly],
                    pass_rate=(sanity.passed) / (sanity.checks_run + 1),
                )
        print(f"    {sanity.passed}/{sanity.checks_run} checks passed")
        for a in sanity.anomalies:
            print(f"    [{a.severity}] {a.check}: {a.message}")
    except Exception as exc:
        print(f"    WARNING: sanity checks unavailable: {exc}")

    print("\n[13] Comparing multi-query results...")
    agreement = None
    if result_b is not None:
        from multi_query.comparator import compare
        agreement = compare(result, result_b)
        if agreement.agreed:
            print("    Approaches AGREE -- high confidence")
        else:
            print("    Approaches DIVERGE:")
            print(f"    {agreement.divergence_detail}")
            print("    Primary result preview:")
            for i, row in enumerate(result.data[:3]):
                print(f"      {i}: {row}")
            print("    Alternative result preview:")
            for i, row in enumerate(result_b.data[:3]):
                print(f"      {i}: {row}")
    else:
        print("    Skipped (no second approach)")

    print("\n[14] Computing confidence...")
    from confidence.scorer import compute_confidence, compute_schema_coverage
    coverage, coverage_flags = compute_schema_coverage(
        sql_result.tables, sql_result.columns, relevant, schema,
    )
    all_flags = coverage_flags
    if sanity is not None:
        all_flags = all_flags + [a.message for a in sanity.anomalies]
    report = compute_confidence(
        syntax_score=1.0,
        alignment=alignment,
        sanity=sanity,
        agreement=agreement,
        coverage=coverage,
        flags=all_flags,
        settings=settings,
    )

    print("\n" + "=" * 60)
    print(f"CONFIDENCE: {report.overall:.1f} / 100")
    print("=" * 60)
    for s in report.signals:
        bar = "#" * int(round(s.score * 20))
        print(f"  {s.name:28s} {s.score:5.2f}  {bar}")
    if report.flags:
        print("\n  Flags:")
        for f in report.flags:
            print(f"    - {f}")

    if settings.block_on_low_confidence and report.overall < settings.min_confidence_score:
        print(f"\n  BLOCKED: confidence {report.overall:.1f} below floor {settings.min_confidence_score}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python main.py "<natural language question>"')
        sys.exit(1)
    question = " ".join(sys.argv[1:])
    run_pipeline(question)
