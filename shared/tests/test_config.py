from __future__ import annotations

import os

from shared.config import Settings


def test_guardrail_defaults():
    os.environ.pop("BLOCK_DDL", None)
    os.environ.pop("BLOCK_DML_WRITES", None)
    os.environ.pop("ENFORCE_ROW_LIMIT", None)
    os.environ.pop("MAX_SUBQUERY_DEPTH", None)
    os.environ.pop("MAX_SCAN_ROWS", None)
    os.environ.pop("READONLY_DATABASE_URL", None)
    s = Settings()
    assert s.block_ddl is True
    assert s.block_dml_writes is True
    assert s.enforce_row_limit == 1000
    assert s.max_subquery_depth == 3
    assert s.max_scan_rows == 100_000
    assert "readonly_user" in s.readonly_db_url


def test_guardrail_overrides_from_env(monkeypatch):
    monkeypatch.setenv("BLOCK_DDL", "false")
    monkeypatch.setenv("ENFORCE_ROW_LIMIT", "500")
    s = Settings()
    assert s.block_ddl is False
    assert s.enforce_row_limit == 500