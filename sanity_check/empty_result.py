from __future__ import annotations

import json

from sanity_check.models import SanityAnomaly
from sanity_check.stats import get_table_row_counts

EMPTY_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "judge_empty_result",
        "description": "Judge whether an empty result is plausible for a question.",
        "parameters": {
            "type": "object",
            "properties": {
                "plausible": {"type": "boolean", "description": "True if 0 rows is plausible"},
                "rationale": {"type": "string", "description": "Why"},
            },
            "required": ["plausible", "rationale"],
        },
    },
}


def check_empty_result(sql, question, result, tables, conn, client, settings) -> SanityAnomaly | None:
    if result.row_count != 0:
        return None
    if not tables:
        return None

    counts = get_table_row_counts(conn, tables)
    if counts and all(c == 0 for c in counts.values()):
        return None

    prompt = (
        f"This SQL produced 0 rows. Question: {question}\nSQL: {sql}\n\n"
        "Is 0 results plausible for this question, or does it indicate the SQL is wrong?"
    )
    response = client.generate_sql_structured(
        prompt=prompt,
        tools=[EMPTY_TOOL_SCHEMA],
        tool_choice="required",
        model=settings.judge_model,
    )
    args = json.loads(response.choices[0].message.tool_calls[0].function.arguments)
    if bool(args["plausible"]):
        return None
    return SanityAnomaly(
        check="empty_result",
        severity="warning",
        message=f"0 rows returned but tables are non-empty: {args['rationale']}",
    )
