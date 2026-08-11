from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    nvidia_api_key: str = field(
        default_factory=lambda: os.getenv("NVIDIA_API_KEY", "")
    )
    nvidia_base_url: str = field(
        default_factory=lambda: os.getenv(
            "NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"
        )
    )
    sql_gen_model: str = field(
        default_factory=lambda: os.getenv(
            "SQL_GEN_MODEL", "deepseek-ai/deepseek-v4-flash"
        )
    )
    judge_model: str = field(
        default_factory=lambda: os.getenv(
            "JUDGE_MODEL", "deepseek-ai/deepseek-v4-pro"
        )
    )
    db_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:123456@localhost:5432/pagila",
        )
    )
    embedding_model: str = field(
        default_factory=lambda: os.getenv(
            "EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"
        )
    )
    similarity_threshold: float = 0.3

    def __post_init__(self) -> None:
        if not self.nvidia_api_key:
            raise ValueError("NVIDIA_API_KEY is not set in .env")
