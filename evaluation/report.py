from __future__ import annotations

import json
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationReport:
    case_results: list
    guardrail_results: list

    def _pct(self, part: int, whole: int) -> float | None:
        return (part / whole * 100.0) if whole else None

    def execution_accuracy(self) -> float | None:
        applicable = [c for c in self.case_results if c.execution.applicable]
        matched = [c for c in applicable if c.execution.matched]
        return self._pct(len(matched), len(applicable))

    def sql_exact_match_pct(self) -> float | None:
        applicable = [c for c in self.case_results if c.sql_match.applicable]
        matched = [c for c in applicable if c.sql_match.matched]
        return self._pct(len(matched), len(applicable))

    def hallucination_detection_rate(self) -> float | None:
        bad = [c for c in self.case_results if c.hallucination.is_bad]
        flagged_bad = [c for c in bad if c.hallucination.flagged]
        return self._pct(len(flagged_bad), len(bad))

    def guardrail_blocked(self) -> int:
        return sum(1 for g in self.guardrail_results if g.blocked)

    def guardrail_total(self) -> int:
        return len(self.guardrail_results)

    def unsafe_queries_executed(self) -> int:
        return sum(1 for g in self.guardrail_results if not g.blocked)

    def headline(self) -> str:
        return (
            f"{_fmt_pct(self.execution_accuracy())}% execution accuracy, "
            f"{_fmt_pct(self.hallucination_detection_rate())}% hallucination detection rate, "
            f"zero unsafe queries executed across {len(self.case_results)} test cases."
        )


def _fmt_pct(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.1f}"


def write_markdown(report: EvaluationReport) -> str:
    lines = [report.headline(), ""]
    lines.append(f"- Execution accuracy: {_fmt_pct(report.execution_accuracy())}%")
    lines.append(f"- SQL exact match: {_fmt_pct(report.sql_exact_match_pct())}%")
    lines.append(f"- Hallucination detection rate: {_fmt_pct(report.hallucination_detection_rate())}%")
    lines.append(f"- Guardrail: {report.guardrail_blocked()}/{report.guardrail_total()} dangerous queries blocked "
                 f"({report.unsafe_queries_executed()} unsafe executed)")
    return "\n".join(lines)


def write_json(report: EvaluationReport, path: str) -> None:
    payload = {
        "headline": report.headline(),
        "execution_accuracy": report.execution_accuracy(),
        "sql_exact_match_pct": report.sql_exact_match_pct(),
        "hallucination_detection_rate": report.hallucination_detection_rate(),
        "guardrail_blocked": report.guardrail_blocked(),
        "guardrail_total": report.guardrail_total(),
        "unsafe_queries_executed": report.unsafe_queries_executed(),
        "total_cases": len(report.case_results),
    }
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
