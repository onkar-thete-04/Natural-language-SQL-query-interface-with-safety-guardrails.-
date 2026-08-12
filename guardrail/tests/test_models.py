from __future__ import annotations

from guardrail.models import GuardrailViolation, GuardrailDecision


def test_violation_fields():
    v = GuardrailViolation(rule="block_ddl", reason="contains DROP")
    assert v.rule == "block_ddl"
    assert v.reason == "contains DROP"


def test_decision_passed_when_no_violations():
    d = GuardrailDecision(passed=True, violations=[])
    assert d.passed is True
    assert d.violations == []


def test_decision_blocked_with_violations():
    v = GuardrailViolation(rule="block_ddl", reason="contains DROP")
    d = GuardrailDecision(passed=False, violations=[v])
    assert d.passed is False
    assert len(d.violations) == 1
    assert d.violations[0] is v
