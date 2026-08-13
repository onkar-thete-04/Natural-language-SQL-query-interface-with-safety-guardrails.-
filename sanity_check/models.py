from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SanityAnomaly:
    check: str
    severity: str
    message: str


@dataclass(frozen=True)
class SanityCheckResult:
    checks_run: int
    passed: int
    anomalies: list[SanityAnomaly]
    pass_rate: float
