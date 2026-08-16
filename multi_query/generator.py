from __future__ import annotations

from sql_generator.models import SQLResult


def generate_alternative(prompt: str, generator) -> SQLResult:
    alt_prompt = (
        f"{prompt}\n\n"
        "Produce an alternative SQL query using a different strategy "
        "(e.g., a different JOIN order, a subquery instead of a JOIN, "
        "or a window function instead of GROUP BY)."
    )
    return generator.generate(alt_prompt)
