from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionResult:
    data: list[dict]
    columns: list[str]
    row_count: int
    execution_time_ms: float
    explain_plan: str
    truncated: bool
