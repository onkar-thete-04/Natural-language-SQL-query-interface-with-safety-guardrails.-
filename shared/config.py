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
    block_ddl: bool = field(
        default_factory=lambda: os.getenv("BLOCK_DDL", "true").lower() == "true"
    )
    block_dml_writes: bool = field(
        default_factory=lambda: os.getenv("BLOCK_DML_WRITES", "true").lower() == "true"
    )
    enforce_row_limit: int = field(
        default_factory=lambda: int(os.getenv("ENFORCE_ROW_LIMIT", "1000"))
    )
    max_subquery_depth: int = field(
        default_factory=lambda: int(os.getenv("MAX_SUBQUERY_DEPTH", "3"))
    )
    max_scan_rows: int = field(
        default_factory=lambda: int(os.getenv("MAX_SCAN_ROWS", "100000"))
    )
    readonly_db_url: str = field(
        default_factory=lambda: os.getenv(
            "READONLY_DATABASE_URL",
            "postgresql://readonly_user:readonly_pass@localhost:5432/pagila",
        )
    )

    def __post_init__(self) -> None:
        if not self.nvidia_api_key:
            raise ValueError("NVIDIA_API_KEY is not set in .env")
