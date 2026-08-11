from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from few_shot_loader import FewShotLoader, render_few_shot_block

from schema_engine.models import Schema
from shared.config import Settings
from prompt_builder.schema_renderer import render_schema_context

SYSTEM_INSTRUCTION = """You are a PostgreSQL expert. Given a database schema and a user question, write a single valid SQL query that answers the question.

Rules:
- Only produce SELECT queries.
- Use the exact table and column names from the provided schema.
- Only query tables listed in the schema context.
- Return ONLY the SQL query, no explanations, no markdown formatting.
- Use proper JOIN syntax for multi-table queries."""


class PromptConstructor:
    def __init__(
        self, schema: Schema, few_shot_loader: FewShotLoader, settings: Settings
    ) -> None:
        self._schema = schema
        self._loader = few_shot_loader
        self._settings = settings

    def build(
        self,
        question: str,
        relevant_tables: list[str],
        constraint: str | None = None,
        clarifications: str | None = None,
    ) -> str:
        examples = self._loader.select(relevant_tables=relevant_tables, top_n=4)
        examples_block = render_few_shot_block(examples)
        schema_block = render_schema_context(self._schema, relevant_tables)

        parts: list[str] = [SYSTEM_INSTRUCTION]

        if clarifications:
            parts.append(f"\n[CLARIFICATION CONTEXT]\n{clarifications}\n")

        if constraint:
            parts.append(f"\n[CONSTRAINT]\n{constraint}\n")

        parts.append(f"\n[SCHEMA]\n{schema_block}\n")

        if examples_block:
            parts.append(f"\n[EXAMPLES]\n{examples_block}\n")

        parts.append(f"\n[QUESTION]\n{question}\n")
        return "\n".join(parts)
