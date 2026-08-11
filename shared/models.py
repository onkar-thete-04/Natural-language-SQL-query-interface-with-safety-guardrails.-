from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Interpretation:
    label: str
    description: str
    example_query: str
    constraint: str


@dataclass(frozen=True)
class ClarificationRequest:
    original_question: str
    interpretations: list[Interpretation]
