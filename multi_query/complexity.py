from __future__ import annotations

from sql_generator.models import SQLResult

_AGGREGATION_KEYWORDS = (
    "count",
    "total",
    "sum",
    "average",
    "avg",
    "how many",
    "minimum",
    "maximum",
    "min ",
    "max ",
    "group by",
    "top ",
    " per ",
)


def is_complex(question: str, sql_result: SQLResult) -> bool:
    sql_upper = sql_result.sql.upper()
    for marker in ("JOIN", "GROUP BY", "UNION", "HAVING", "("):
        if marker in sql_upper:
            return True

    question_lower = question.lower()
    return any(kw in question_lower for kw in _AGGREGATION_KEYWORDS)
