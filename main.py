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

    print("\n[7] Running guardrail checks...")
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

    print("\n[8] Opening sandbox session (read-only)...")
    from sandbox.engine import create_readonly_engine, read_only_session
    readonly_engine = create_readonly_engine(settings.readonly_db_url)

    print("\n[9] Executing query...")
    from executor.runner import execute
    try:
        with read_only_session(readonly_engine) as conn:
            result = execute(guarded_sql, conn, row_limit=settings.enforce_row_limit)
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


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python main.py "<natural language question>"')
        sys.exit(1)
    question = " ".join(sys.argv[1:])
    run_pipeline(question)
