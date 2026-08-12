from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SQLResult:
    sql: str
    explanation: str
    confidence: float
    tables: list[str]
    columns: list[str]
