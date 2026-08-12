from __future__ import annotations

import re

import sqlparse
from sqlparse.sql import Parenthesis, Statement
from sqlparse.tokens import Keyword

from guardrail.models import GuardrailViolation

DDL_KEYWORDS = {"CREATE", "ALTER", "DROP", "TRUNCATE", "GRANT", "REVOKE"}
DML_WRITE_KEYWORDS = {"INSERT", "UPDATE", "DELETE", "MERGE"}

_DDL_PATTERN = re.compile(
    r"\b(" + "|".join(sorted(DDL_KEYWORDS)) + r")\b", re.IGNORECASE
)
_DML_PATTERN = re.compile(
    r"\b(" + "|".join(sorted(DML_WRITE_KEYWORDS)) + r")\b", re.IGNORECASE
)


def block_ddl(sql: str) -> GuardrailViolation | None:
    parsed = sqlparse.parse(sql)
    if not parsed:
        return None
    stmt = parsed[0]
    for tok in stmt.flatten():
        if tok.ttype in Keyword:
            kw = tok.value.upper()
            if kw in DDL_KEYWORDS:
                return GuardrailViolation(rule="block_ddl", reason=f"DDL keyword '{kw}' detected")
    match = _DDL_PATTERN.search(stmt.value)
    if match:
        kw = match.group(1).upper()
        return GuardrailViolation(rule="block_ddl", reason=f"DDL keyword '{kw}' detected")
    return None


def block_dml_writes(sql: str) -> GuardrailViolation | None:
    parsed = sqlparse.parse(sql)
    if not parsed:
        return None
    stmt = parsed[0]
    first_keyword = _first_keyword(stmt)
    if first_keyword in DML_WRITE_KEYWORDS:
        return GuardrailViolation(rule="block_dml_writes", reason=f"DML write '{first_keyword}' detected")
    for tok in stmt.flatten():
        if tok.ttype in Keyword:
            kw = tok.value.upper()
            if kw in DML_WRITE_KEYWORDS:
                return GuardrailViolation(rule="block_dml_writes", reason=f"DML write '{kw}' detected")
    match = _DML_PATTERN.search(stmt.value)
    if match:
        kw = match.group(1).upper()
        return GuardrailViolation(rule="block_dml_writes", reason=f"DML write '{kw}' detected")
    return None


def _first_keyword(stmt: Statement) -> str | None:
    for tok in stmt.tokens:
        if tok.ttype in Keyword:
            return tok.value.upper()
    match = re.match(r"\s*(\w+)", stmt.value)
    if match:
        return match.group(1).upper()
    return None


def enforce_row_limit(sql: str, limit: int) -> tuple[str, GuardrailViolation | None]:
    limit_pattern = re.compile(r"\bLIMIT\s+(\d+)\b", re.IGNORECASE)
    match = limit_pattern.search(sql)
    if match:
        existing = int(match.group(1))
        if existing > limit:
            new_sql = limit_pattern.sub(f"LIMIT {limit}", sql, count=1)
            return new_sql, GuardrailViolation(
                rule="enforce_row_limit",
                reason=f"LIMIT reduced from {existing} to {limit}",
            )
        return sql, None
    new_sql = f"{sql.rstrip(';').rstrip()} LIMIT {limit};"
    return new_sql, None


def check_subquery_depth(sql: str, max_depth: int) -> GuardrailViolation | None:
    parsed = sqlparse.parse(sql)
    if not parsed:
        return None
    stmt = parsed[0]
    depth = _count_subquery_depth(stmt)
    if depth > max_depth:
        return GuardrailViolation(
            rule="check_subquery_depth",
            reason=f"Subquery nesting depth {depth} exceeds max {max_depth}",
        )
    return None


def _count_subquery_depth(stmt: Statement) -> int:
    def _depth_of(token) -> int:
        if isinstance(token, Parenthesis):
            inner_max = 0
            for inner in token.tokens:
                inner_max = max(inner_max, _depth_of(inner))
            return 1 + inner_max
        if hasattr(token, "tokens"):
            d = 0
            for inner in token.tokens:
                d = max(d, _depth_of(inner))
            return d
        return 0
    return _depth_of(stmt)


import re as _re

from sqlalchemy import text as _text


def estimate_scan_cost(
    sql: str, engine: object, max_scan_rows: int
) -> GuardrailViolation | None:
    rows_estimate = _estimate_rows(sql, engine)
    if rows_estimate is None:
        return None
    if rows_estimate > max_scan_rows:
        return GuardrailViolation(
            rule="estimate_scan_cost",
            reason=f"Estimated scan rows {rows_estimate} exceeds max {max_scan_rows}",
        )
    return None


def _estimate_rows(sql: str, engine: object) -> int | None:
    try:
        with engine.connect() as conn:
            result = conn.execute(_text(f"EXPLAIN {sql}")).fetchall()
    except Exception:
        return None
    total = 0
    found_any = False
    for row in result:
        line = row[0] if isinstance(row, (tuple, list)) else str(row)
        line_str = str(line)
        match = _re.search(r"rows=(\d+)", line_str)
        if match:
            total += int(match.group(1))
            found_any = True
    return total if found_any else None