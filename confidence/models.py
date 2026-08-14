from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfidenceSignal:
    name: str
    score: float
    weight: float
    detail: str


@dataclass(frozen=True)
class ConfidenceReport:
    overall: float
    signals: list[ConfidenceSignal]
    flags: list[str]
