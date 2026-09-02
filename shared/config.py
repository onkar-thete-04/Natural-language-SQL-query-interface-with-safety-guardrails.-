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
    back_translation_embed_pass_threshold: float = field(
        default_factory=lambda: float(
            os.getenv("BACK_TRANSLATION_EMBED_PASS_THRESHOLD", "0.92")
        )
    )
    back_translation_embed_fail_threshold: float = field(
        default_factory=lambda: float(
            os.getenv("BACK_TRANSLATION_EMBED_FAIL_THRESHOLD", "0.70")
        )
    )
    sanity_null_threshold: float = field(
        default_factory=lambda: float(os.getenv("SANITY_NULL_THRESHOLD", "0.80"))
    )
    block_on_low_confidence: bool = field(
        default_factory=lambda: os.getenv("BLOCK_ON_LOW_CONFIDENCE", "false").lower() == "true"
    )
    min_confidence_score: float = field(
        default_factory=lambda: float(os.getenv("MIN_CONFIDENCE_SCORE", "60.0"))
    )
    confidence_weight_syntax: float = field(
        default_factory=lambda: float(os.getenv("CONFIDENCE_WEIGHT_SYNTAX", "0.10"))
    )
    confidence_weight_alignment: float = field(
        default_factory=lambda: float(os.getenv("CONFIDENCE_WEIGHT_ALIGNMENT", "0.30"))
    )
    confidence_weight_sanity: float = field(
        default_factory=lambda: float(os.getenv("CONFIDENCE_WEIGHT_SANITY", "0.25"))
    )
    confidence_weight_agreement: float = field(
        default_factory=lambda: float(os.getenv("CONFIDENCE_WEIGHT_AGREEMENT", "0.20"))
    )
    confidence_weight_coverage: float = field(
        default_factory=lambda: float(os.getenv("CONFIDENCE_WEIGHT_COVERAGE", "0.15"))
    )
    sqlite_db_path: str = field(
        default_factory=lambda: os.getenv(
            "SQLITE_DB_PATH", "store/text_to_sql.db"
        )
    )
    few_shot_feedback_path: str = field(
        default_factory=lambda: os.getenv(
            "FEW_SHOT_FEEDBACK_PATH", "few_shot_feedback.yaml"
        )
    )
    eval_test_cases_path: str = field(
        default_factory=lambda: os.getenv(
            "EVAL_TEST_CASES_PATH", "eval/test_cases.yaml"
        )
    )
    api_host: str = field(
        default_factory=lambda: os.getenv("API_HOST", "127.0.0.1")
    )
    api_port: int = field(
        default_factory=lambda: int(os.getenv("API_PORT", "8000"))
    )
    api_base_url: str = field(
        default_factory=lambda: os.getenv(
            "API_BASE_URL", "http://127.0.0.1:8000"
        )
    llm_rate_limit_rpm: int = field(
        default_factory=lambda: int(os.getenv("LLM_RATE_LIMIT_RPM", "35"))
    )
    llm_retry_max_attempts: int = field(
        default_factory=lambda: int(os.getenv("LLM_RETRY_MAX_ATTEMPTS", "4"))
    )
    llm_retry_base_delay: float = field(
        default_factory=lambda: float(os.getenv("LLM_RETRY_BASE_DELAY", "2.0"))
    )
    llm_retry_max_delay: float = field(
        default_factory=lambda: float(os.getenv("LLM_RETRY_MAX_DELAY", "60.0"))
    )
    llm_timeout_seconds: float = field(
        default_factory=lambda: float(os.getenv("LLM_TIMEOUT_SECONDS", "120"))
    )

    def __post_init__(self) -> None:
        if not self.nvidia_api_key:
            raise ValueError("NVIDIA_API_KEY is not set in .env")
