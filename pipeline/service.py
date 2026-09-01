from __future__ import annotations

from pipeline.models import PipelineResult


class PipelineService:
    def __init__(self, settings=None) -> None:
        from shared.config import Settings
        self.settings = settings or Settings()
        self._schema = None
        self._embedder = None
        self._client = None

    def get_schema(self):
        return self._get_schema()

    def _get_schema(self):
        if self._schema is None:
            from schema_engine.introspector import SchemaIntrospector
            introspector = SchemaIntrospector(self.settings.db_url)
            schema = introspector.introspect()
            try:
                from sqlalchemy import create_engine
                engine = create_engine(self.settings.db_url)
                from schema_engine.sampler import enrich_schema_with_samples
                schema = enrich_schema_with_samples(schema, engine, limit=5)
            except Exception:
                pass
            self._schema = schema
        return self._schema

    def _get_embedder(self):
        if self._embedder is None:
            from relevance_filter.embedder import SchemaEmbedder
            self._embedder = SchemaEmbedder(self.settings.embedding_model)
        return self._embedder

    def _get_client(self):
        if self._client is None:
            from shared.llm_client import LLMClient
            self._client = LLMClient(self.settings)
        return self._client

    def run(self, question: str) -> PipelineResult:
        settings = self.settings
        schema = self._get_schema()
        embedder = self._get_embedder()
        client = self._get_client()

        from relevance_filter.scorer import RelevanceScorer
        scorer = RelevanceScorer(embedder, schema, threshold=settings.similarity_threshold)
        relevant = scorer.score_tables(question)

        from ambiguity_resolver.detector import AmbiguityDetector
        detector = AmbiguityDetector(embedder, schema)
        clarification = detector.detect(question)
        clarifications_text = None
        constraint = None
        if clarification:
            chosen = clarification.interpretations[0]
            clarifications_text = f"User selected: {chosen.label}"
            constraint = chosen.constraint

        from prompt_builder.constructor import PromptConstructor
        from few_shot_loader import FewShotLoader
        loader = FewShotLoader(feedback_path=self.settings.few_shot_feedback_path)
        constructor = PromptConstructor(schema, loader, settings)
        prompt = constructor.build(
            question=question,
            relevant_tables=relevant,
            constraint=constraint,
            clarifications=clarifications_text,
        )

        from sql_generator.generator import SQLGenerator
        generator = SQLGenerator(client=client, max_retries=3)
        sql_result = generator.generate(prompt)

        alignment = None
        try:
            from back_translation.translator import back_translate
            from back_translation.aligner import align
            back_translated = back_translate(sql_result.sql, client, settings)
            alignment = align(question, back_translated, embedder, client, settings)
        except Exception:
            alignment = None

        second_sql_result = None
        from multi_query.complexity import is_complex
        from multi_query.generator import generate_alternative
        if is_complex(question, sql_result):
            try:
                second_sql_result = generate_alternative(prompt, generator)
            except Exception:
                second_sql_result = None

        from sqlalchemy import create_engine
        guardrail_engine = create_engine(settings.db_url)
        guarded_sql, decision = self._guard(guardrail_engine, sql_result.sql)

        from sandbox.engine import create_readonly_engine, read_only_session
        readonly_engine = create_readonly_engine(settings.readonly_db_url)

        from executor.runner import execute
        with read_only_session(readonly_engine) as conn:
            result = execute(guarded_sql, conn, row_limit=settings.enforce_row_limit)
            result_b = None
            if second_sql_result is not None:
                try:
                    alt_sql, alt_decision = self._guard(guardrail_engine, second_sql_result.sql)
                    if alt_decision.passed:
                        result_b = execute(alt_sql, conn, row_limit=settings.enforce_row_limit)
                except Exception:
                    result_b = None

        sanity = self._run_sanity(readonly_engine, guarded_sql, question, result, sql_result, client)

        agreement = None
        if result_b is not None:
            from multi_query.comparator import compare
            agreement = compare(result, result_b)

        from confidence.scorer import compute_confidence, compute_schema_coverage
        coverage, coverage_flags = compute_schema_coverage(
            sql_result.tables, sql_result.columns, relevant, schema,
        )
        all_flags = list(coverage_flags)
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

        return PipelineResult(
            question=question,
            generated_sql=sql_result,
            guarded_sql=guarded_sql,
            alignment=alignment,
            second_sql=second_sql_result,
            guardrail=decision,
            execution=result,
            sanity=sanity,
            agreement=agreement,
            confidence_report=report,
            clarification=clarification,
        )

    def run_sql(self, sql: str) -> dict:
        """Run guardrail -> sandbox -> execution on caller-supplied SQL (the
        frontend's 'Run edited SQL' path). No generation, no storage, no
        flywheel. Returns {'execution': ..., 'guardrail': ...}."""
        from sqlalchemy import create_engine
        guardrail_engine = create_engine(self.settings.db_url)
        guarded_sql, decision = self._guard(guardrail_engine, sql)

        from sandbox.engine import create_readonly_engine, read_only_session
        readonly_engine = create_readonly_engine(self.settings.readonly_db_url)
        from executor.runner import execute
        with read_only_session(readonly_engine) as conn:
            execution = execute(guarded_sql, conn, row_limit=self.settings.enforce_row_limit)

        from shared.serialization import to_dict
        return {
            "execution": to_dict(execution),
            "guardrail": to_dict(decision),
            "guarded_sql": guarded_sql,
        }

    def _guard(self, engine, sql):
        from guardrail.validator import validate
        from shared.errors import GuardrailError
        guarded_sql, decision = validate(sql, self.settings, engine)
        if not decision.passed:
            raise GuardrailError(
                "; ".join(f"[{v.rule}] {v.reason}" for v in decision.violations)
            )
        return guarded_sql, decision

    def _run_sanity(self, readonly_engine, sql, question, result, sql_result, client):
        try:
            from sanity_check.checks import run_checks
            from sanity_check.models import SanityCheckResult
            from sanity_check.empty_result import check_empty_result
            from sandbox.engine import read_only_session
            with read_only_session(readonly_engine) as conn:
                sanity = run_checks(
                    sql, result, sql_result.tables, sql_result.columns, conn, self.settings,
                )
                empty_anomaly = check_empty_result(
                    sql, question, result, sql_result.tables, conn, client, self.settings,
                )
                if empty_anomaly is not None:
                    sanity = SanityCheckResult(
                        checks_run=sanity.checks_run + 1,
                        passed=sanity.passed,
                        anomalies=sanity.anomalies + [empty_anomaly],
                        pass_rate=sanity.passed / (sanity.checks_run + 1),
                    )
                return sanity
        except Exception:
            return None
