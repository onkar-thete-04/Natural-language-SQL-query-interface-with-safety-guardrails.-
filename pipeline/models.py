from __future__ import annotations

from dataclasses import dataclass

from back_translation.models import AlignmentResult
from confidence.models import ConfidenceReport
from executor.models import ExecutionResult
from guardrail.models import GuardrailDecision
from multi_query.models import AgreementResult
from sanity_check.models import SanityCheckResult
from shared.models import ClarificationRequest
from sql_generator.models import SQLResult


@dataclass(frozen=True)
class PipelineResult:
    question: str
    generated_sql: SQLResult
    guarded_sql: str
    alignment: AlignmentResult | None
    second_sql: SQLResult | None
    guardrail: GuardrailDecision
    execution: ExecutionResult
    sanity: SanityCheckResult | None
    agreement: AgreementResult | None
    confidence_report: ConfidenceReport
    clarification: ClarificationRequest | None
