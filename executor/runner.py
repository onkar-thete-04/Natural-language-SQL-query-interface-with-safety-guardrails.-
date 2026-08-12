from __future__ import annotations

import time

from sqlalchemy import text

from executor.models import ExecutionResult
from shared.errors import ExecutionError


def execute(sql: str, conn: object, row_limit: int) -> ExecutionResult:
    try:
        explain_rows = conn.execute(text(f"EXPLAIN {sql}")).fetchall()
    except Exception as exc:
        raise ExecutionError(f"EXPLAIN failed: {exc}") from exc
    explain_plan = "\n".join(r[0] if isinstance(r, (tuple, list)) else str(r) for r in explain_rows)

    start = time.perf_counter()
    try:
        result_proxy = conn.execute(text(sql))
        rows = result_proxy.mappings().all()
    except Exception as exc:
        raise ExecutionError(f"Query execution failed: {exc}") from exc
    elapsed_ms = (time.perf_counter() - start) * 1000

    data = [dict(row) for row in rows]
    columns = list(result_proxy.keys())
    truncated = len(data) >= row_limit

    return ExecutionResult(
        data=data,
        columns=columns,
        row_count=len(data),
        execution_time_ms=round(elapsed_ms, 2),
        explain_plan=explain_plan,
        truncated=truncated,
    )
