from __future__ import annotations

import json
from typing import Any

import sqlparse

from shared.errors import SQLValidationError
from sql_generator.models import SQLResult

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "generate_sql",
        "description": "Generate a SQL query with metadata for a natural language question.",
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "The SQL query"},
                "explanation": {"type": "string", "description": "Natural language explanation of the query"},
                "confidence": {"type": "number", "description": "Confidence score 0.0 to 1.0"},
                "tables": {"type": "array", "items": {"type": "string"}, "description": "Tables accessed"},
                "columns": {"type": "array", "items": {"type": "string"}, "description": "Columns accessed"},
            },
            "required": ["sql", "explanation", "confidence", "tables", "columns"],
        },
    },
}


class SQLGenerator:
    def __init__(self, client: Any, max_retries: int = 3) -> None:
        self._client = client
        self._max_retries = max_retries

    def generate(self, prompt: str) -> SQLResult:
        messages = [{"role": "user", "content": prompt}]
        last_error = ""
        for _ in range(self._max_retries):
            try:
                response = self._client.generate_sql_structured(
                    prompt=prompt,
                    messages=messages,
                    tools=[TOOL_SCHEMA],
                    tool_choice="required",
                )
                result = self._parse_response(response)
                self._validate_sql(result.sql)
                return result
            except (SQLValidationError, ValueError, KeyError) as exc:
                last_error = str(exc)
                messages.append({"role": "system", "content": f"Previous attempt failed: {last_error}. Please regenerate."})
        raise SQLValidationError(f"Structured output failed after {self._max_retries} retries: {last_error}")

    def _parse_response(self, response: Any) -> SQLResult:
        if not response.choices or not response.choices[0].message.tool_calls:
            raise SQLValidationError("No tool calls in response")
        args_raw = response.choices[0].message.tool_calls[0].function.arguments
        try:
            args = json.loads(args_raw)
        except (json.JSONDecodeError, TypeError) as exc:
            raise SQLValidationError(f"Failed to parse tool arguments as JSON: {exc}") from exc
        required = ["sql", "explanation", "confidence", "tables", "columns"]
        for field in required:
            if field not in args:
                raise SQLValidationError(f"missing required field: {field}")
        confidence = float(args["confidence"])
        confidence = max(0.0, min(1.0, confidence))
        return SQLResult(
            sql=args["sql"],
            explanation=args["explanation"],
            confidence=confidence,
            tables=list(args["tables"]),
            columns=list(args["columns"]),
        )

    def _validate_sql(self, sql: str) -> None:
        statements = sqlparse.parse(sql)
        non_empty = [s for s in statements if str(s).strip()]
        if len(non_empty) == 0:
            raise SQLValidationError("Empty SQL")
        if len(non_empty) > 1:
            raise SQLValidationError("SQL must be a single statement")