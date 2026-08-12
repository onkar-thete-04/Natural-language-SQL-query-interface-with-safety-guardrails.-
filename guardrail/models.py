from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GuardrailViolation:
    rule: str
    reason: str


@dataclass(frozen=True)
class GuardrailDecision:
    passed: bool
    violations: list[GuardrailViolation]