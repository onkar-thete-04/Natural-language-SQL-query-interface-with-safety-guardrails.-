from __future__ import annotations

import random
import threading
import time
from collections import deque

from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    NotFoundError,
    OpenAI,
    RateLimitError,
)

from shared.config import Settings
from shared.errors import LLMClientError

_RETRYABLE_EXCEPTIONS = (
    RateLimitError,
    InternalServerError,
    APITimeoutError,
    APIConnectionError,
    NotFoundError,
)


class _SlidingWindowRateLimiter:
    def __init__(self, rpm: int, window_seconds: float = 60.0) -> None:
        self._limit = max(1, int(rpm))
        self._window = window_seconds
        self._timestamps: deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        with self._lock:
            now = time.monotonic()
            self._evict(now)
            if len(self._timestamps) >= self._limit:
                wait = self._timestamps[0] + self._window - now + 0.05
                if wait > 0:
                    time.sleep(wait)
                    now = time.monotonic()
                    self._evict(now)
            self._timestamps.append(now)

    def _evict(self, now: float) -> None:
        while self._timestamps and now - self._timestamps[0] > self._window:
            self._timestamps.popleft()


class LLMClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        self._client = OpenAI(
            base_url=self._settings.nvidia_base_url,
            api_key=self._settings.nvidia_api_key,
        )
        self._limiter = _SlidingWindowRateLimiter(self._settings.llm_rate_limit_rpm)

    def generate_sql(self, prompt: str, model: str | None = None) -> str:
        model_name = model or self._settings.sql_gen_model

        def _call() -> str:
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

        return self._with_retry(_call)

    def generate_sql_structured(
        self,
        prompt: str,
        tools: list[dict],
        tool_choice: str = "required",
        messages: list[dict] | None = None,
        model: str | None = None,
    ) -> object:
        model_name = model or self._settings.sql_gen_model
        if messages is None:
            messages = [{"role": "user", "content": prompt}]

        def _call() -> object:
            return self._client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=tools,
                tool_choice=tool_choice,
                temperature=0.0,
                max_tokens=1024,
            )

        return self._with_retry(_call)

    def _with_retry(self, fn):
        last_exc = None
        for attempt in range(self._settings.llm_retry_max_attempts):
            self._limiter.acquire()
            try:
                return fn()
            except LLMClientError:
                raise
            except Exception as exc:
                if not isinstance(exc, _RETRYABLE_EXCEPTIONS):
                    raise LLMClientError(f"LLM call failed: {exc}") from exc
                last_exc = exc
                if attempt < self._settings.llm_retry_max_attempts - 1:
                    time.sleep(self._backoff_delay(attempt))
        raise LLMClientError(
            f"LLM call failed after {self._settings.llm_retry_max_attempts} attempts: {last_exc}"
        ) from last_exc

    def _backoff_delay(self, attempt: int) -> float:
        base = self._settings.llm_retry_base_delay
        cap = self._settings.llm_retry_max_delay
        return min(cap, base * (2 ** attempt)) * random.random()
