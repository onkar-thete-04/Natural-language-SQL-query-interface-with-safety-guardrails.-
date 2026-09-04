from __future__ import annotations

import re
from dataclasses import dataclass

import sqlparse

from evaluation.dataset import GoldenCase

_OPERATOR_RE = re.compile(r"\s*(<=|>=|<>|!=|=|<|>)\s*")


@dataclass(frozen=True)
class SqlMatchResult:
    case_id: str
    applicable: bool
    matched: bool | None


def normalize_sql(sql: str) -> str:
    formatted = sqlparse.format(sql, keyword_case="upper", identifier_case="lower", strip_comments=True)
    formatted = _OPERATOR_RE.sub(r" \1 ", formatted)
    collapsed = " ".join(formatted.split())
    return collapsed.rstrip(";").strip()


def sql_exact_match(generated: str, gold: str | list[str]) -> bool:
    if isinstance(gold, list):
        return any(sql_exact_match(generated, g) for g in gold)
    return normalize_sql(generated) == normalize_sql(gold)


def evaluate(case: GoldenCase, result) -> SqlMatchResult:
    if case.category == "unanswerable" or case.gold_sql is None:
        return SqlMatchResult(case.id, False, None)
    return SqlMatchResult(case.id, True, sql_exact_match(result.generated_sql.sql, case.gold_sql))
