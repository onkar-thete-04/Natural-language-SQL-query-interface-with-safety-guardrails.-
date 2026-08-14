from __future__ import annotations

from back_translation.models import AlignmentResult
from confidence.models import ConfidenceReport, ConfidenceSignal
from multi_query.models import AgreementResult
from sanity_check.models import SanityCheckResult
from schema_engine.models import Schema


def compute_schema_coverage(
    tables: list[str],
    columns: list[str],
    relevant_tables: list[str],
    schema: Schema,
) -> tuple[float, list[str]]:
    flags: list[str] = []
    if not tables:
        return 0.0, flags

    relevant_lower = {r.lower() for r in relevant_tables}
    if relevant_lower:
        matched = sum(1 for t in tables if t.lower() in relevant_lower)
        coverage = matched / len(tables)
        for t in tables:
            if t.lower() not in relevant_lower:
                flags.append(f"table '{t}' not in the relevant set")
    else:
        coverage = 1.0

    if columns:
        known = set()
        for table in schema.tables:
            if not relevant_lower or table.name.lower() in relevant_lower:
                for c in table.columns:
                    known.add(c.name.lower())
        for c in columns:
            if c.lower() not in known and "*" not in c:
                flags.append(f"column '{c}' not found in relevant tables")

    return coverage, flags


def compute_confidence(
    syntax_score: float,
    alignment: AlignmentResult | None,
    sanity: SanityCheckResult | None,
    agreement: AgreementResult | None,
    coverage: float,
    flags: list[str],
    settings,
) -> ConfidenceReport:
    signals: list[ConfidenceSignal] = []

    signals.append(ConfidenceSignal(
        name="sql_syntax",
        score=syntax_score,
        weight=settings.confidence_weight_syntax,
        detail="SQL generated, validated, and passed guardrail",
    ))

    if alignment is not None:
        signals.append(ConfidenceSignal(
            name="back_translation_alignment",
            score=alignment.alignment_score,
            weight=settings.confidence_weight_alignment,
            detail=f"method={alignment.method}",
        ))

    if sanity is not None:
        signals.append(ConfidenceSignal(
            name="sanity_checks",
            score=sanity.pass_rate,
            weight=settings.confidence_weight_sanity,
            detail=f"{sanity.passed}/{sanity.checks_run} checks passed",
        ))

    if agreement is not None:
        signals.append(ConfidenceSignal(
            name="multi_query_agreement",
            score=1.0 if agreement.agreed else 0.0,
            weight=settings.confidence_weight_agreement,
            detail="agreed" if agreement.agreed else "diverged",
        ))

    signals.append(ConfidenceSignal(
        name="schema_coverage",
        score=coverage,
        weight=settings.confidence_weight_coverage,
        detail="table/column coverage vs relevant set",
    ))

    total_weight = sum(s.weight for s in signals)
    weighted = sum(s.score * s.weight for s in signals)
    overall = 100.0 * weighted / total_weight if total_weight else 0.0

    return ConfidenceReport(
        overall=round(overall, 1),
        signals=signals,
        flags=flags,
    )
