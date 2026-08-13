from __future__ import annotations

from shared.llm_client import LLMClient
from shared.config import Settings


def back_translate(sql: str, client: LLMClient, settings: Settings) -> str:
    prompt = (
        "Here is a SQL query:\n"
        f"{sql}\n\n"
        "What question does this SQL query answer? "
        "Reply with a single natural-language question and nothing else."
    )
    return client.generate_sql(prompt, model=settings.judge_model).strip()
