from __future__ import annotations

from unittest.mock import MagicMock

from guardrail.validator import validate
from guardrail.models import GuardrailDecision
from shared.config import Settings


def _mock_engine(rows_estimate: str = "rows=5"):
    engine = MagicMock()
    conn = MagicMock()
    engine.connect.return_value.__enter__.return_value = conn
    conn.execute.return_value.fetchall.return_value = [(rows_estimate,)]
    return engine


def test_validate_passes_clean_select():
    settings = MagicMock()
    settings.block_ddl = True
    settings.block_dml_writes = True
    settings.enforce_row_limit = 1000
    settings.max_subquery_depth = 3
    settings.max_scan_rows = 100_000
    engine = _mock_engine("rows=10")
    sql, decision = validate("SELECT * FROM customer", settings, engine)
    assert decision.passed is True
    assert decision.violations == []
    assert "LIMIT 1000" in sql.upper()


def test_validate_blocks_ddl():
    settings = MagicMock()
    settings.block_ddl = True
    settings.block_dml_writes = True
    settings.enforce_row_limit = 1000
    settings.max_subquery_depth = 3
    settings.max_scan_rows = 100_000
    engine = _mock_engine()
    sql, decision = validate("DROP TABLE customer", settings, engine)
    assert decision.passed is False
    assert any(v.rule == "block_ddl" for v in decision.violations)


def test_validate_blocks_dml():
    settings = MagicMock()
    settings.block_ddl = True
    settings.block_dml_writes = True
    settings.enforce_row_limit = 1000
    settings.max_subquery_depth = 3
    settings.max_scan_rows = 100_000
    engine = _mock_engine()
    sql, decision = validate("DELETE FROM customer", settings, engine)
    assert decision.passed is False
    assert any(v.rule == "block_dml_writes" for v in decision.violations)


def test_validate_disabling_ddl_skips_check():
    settings = MagicMock()
    settings.block_ddl = False
    settings.block_dml_writes = True
    settings.enforce_row_limit = 1000
    settings.max_subquery_depth = 3
    settings.max_scan_rows = 100_000
    engine = _mock_engine()
    sql, decision = validate("DROP TABLE customer", settings, engine)
    assert "block_ddl" not in [v.rule for v in decision.violations]
