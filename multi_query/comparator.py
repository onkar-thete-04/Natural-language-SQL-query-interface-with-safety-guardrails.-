from __future__ import annotations

from executor.models import ExecutionResult
from multi_query.models import AgreementResult


def _row_key(row: dict) -> tuple:
    return tuple(sorted((k, str(v)) for k, v in row.items()))


def compare(a: ExecutionResult, b: ExecutionResult) -> AgreementResult:
    if a.row_count == 0 and b.row_count == 0:
        return AgreementResult(agreed=True, identical=True, row_counts=(0, 0), divergence_detail=None)

    if a.columns == b.columns:
        set_a = {_row_key(r) for r in a.data}
        set_b = {_row_key(r) for r in b.data}
        if set_a == set_b:
            return AgreementResult(
                agreed=True,
                identical=True,
                row_counts=(a.row_count, b.row_count),
                divergence_detail=None,
            )
        return AgreementResult(
            agreed=False,
            identical=False,
            row_counts=(a.row_count, b.row_count),
            divergence_detail="row sets differ",
        )

    if a.row_count == b.row_count:
        return AgreementResult(
            agreed=True,
            identical=False,
            row_counts=(a.row_count, b.row_count),
            divergence_detail="row counts match (columns differ)",
        )
    return AgreementResult(
        agreed=False,
        identical=False,
        row_counts=(a.row_count, b.row_count),
        divergence_detail=f"row counts differ: {a.row_count} vs {b.row_count}",
    )
