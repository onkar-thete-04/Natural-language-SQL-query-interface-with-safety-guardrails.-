from __future__ import annotations

import sys


def run_pipeline(question: str) -> None:
    from shared.config import Settings
    from shared.errors import SchemaIntrospectionError, LLMClientError

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

    print("\n[6] Calling LLM...")
    try:
        from shared.llm_client import LLMClient
        client = LLMClient(settings)
        sql = client.generate_sql(prompt)
        print("\n" + "=" * 60)
        print("GENERATED SQL")
        print("=" * 60)
        print(sql)
        print("=" * 60)
    except LLMClientError as exc:
        print(f"LLM call failed: {exc}")
        print("(Prompt was built successfully, but API call failed)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python main.py "<natural language question>"')
        sys.exit(1)
    question = " ".join(sys.argv[1:])
    run_pipeline(question)
