from __future__ import annotations

from openai import OpenAI

from shared.config import Settings
from shared.errors import LLMClientError


class LLMClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        self._client = OpenAI(
            base_url=self._settings.nvidia_base_url,
            api_key=self._settings.nvidia_api_key,
        )

    def generate_sql(self, prompt: str, model: str | None = None) -> str:
        model_name = model or self._settings.sql_gen_model
        try:
            response = self._client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=1024,
            )
            content = response.choices[0].message.content
            if content is None:
                raise LLMClientError("LLM returned empty response")
            return content
        except Exception as exc:
            raise LLMClientError(f"LLM call failed: {exc}") from exc
