from __future__ import annotations

import json
import re
from types import SimpleNamespace

from pipeline.service import PipelineService

DEFAULT_TABLES = ["film"]
DEFAULT_COLUMNS = ["film_id", "title"]

_FROM_RE = re.compile(
    r"\bfrom\s+([a-zA-Z_][\w]*(\s*,\s*[a-zA-Z_][\w]*)*)",
    re.IGNORECASE,
)


def _extract_tables(sql: str) -> list[str]:
    match = _FROM_RE.search(sql)
    if not match:
        return DEFAULT_TABLES
    return [name.strip() for name in match.group(1).split(",")]


def _tool_response(args: dict) -> object:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    tool_calls=[
                        SimpleNamespace(
                            function=SimpleNamespace(arguments=json.dumps(args))
                        )
                    ]
                )
            )
        ]
    )


class ScriptedLLMClient:
    def __init__(self, script: dict[str, str]) -> None:
        self._script = script
        self.current_question: str | None = None

    def generate_sql(self, prompt: str, model: str | None = None) -> str:
        return self.current_question or "scripted back-translation"

    def generate_sql_structured(self, prompt, tools, tool_choice="required", messages=None, model=None) -> object:
        tool_name = tools[0]["function"]["name"]
        if tool_name == "score_alignment":
            return _tool_response({"score": 1.0, "rationale": "scripted"})
        if tool_name == "judge_empty_result":
            return _tool_response({"plausible": True, "rationale": "scripted"})
        canned = self._script[self.current_question]
        return _tool_response({
            "sql": canned,
            "explanation": "scripted",
            "confidence": 0.9,
            "tables": _extract_tables(canned),
            "columns": DEFAULT_COLUMNS,
        })


class OfflinePipelineService(PipelineService):
    def __init__(self, settings, script: dict[str, str]) -> None:
        super().__init__(settings)
        self._script = script

    def _get_client(self):
        if self._client is None:
            self._client = ScriptedLLMClient(self._script)
        return self._client

    def run(self, question: str):
        client = self._get_client()
        client.current_question = question
        return super().run(question)
