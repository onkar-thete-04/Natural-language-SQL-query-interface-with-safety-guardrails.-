from __future__ import annotations

import pytest

from guardrail.models import GuardrailViolation
from guardrail.rules import (
    block_ddl,
    block_dml_writes,
    enforce_row_limit,
    check_subquery_depth,
)


# --- block_ddl ---

def test_block_ddl_detects_create():
    v = block_ddl("CREATE TABLE foo (id int)")
    assert v is not None
    assert v.rule == "block_ddl"
    assert "CREATE" in v.reason


def test_block_ddl_detects_drop():
    v = block_ddl("DROP TABLE customer")
    assert v is not None
    assert "DROP" in v.reason


def test_block_ddl_detects_truncate():
    v = block_ddl("TRUNCATE TABLE rental")
    assert v is not None


def test_block_ddl_allows_select():
    v = block_ddl("SELECT * FROM customer")
    assert v is None


def test_block_ddl_detects_alter():
    v = block_ddl("ALTER TABLE customer ADD COLUMN x int")
    assert v is not None


# --- block_dml_writes ---

def test_block_dml_detects_insert():
    v = block_dml_writes("INSERT INTO customer VALUES (1)")
    assert v is not None
    assert v.rule == "block_dml_writes"
    assert "INSERT" in v.reason


def test_block_dml_detects_update():
    v = block_dml_writes("UPDATE customer SET first_name = 'X'")
    assert v is not None


def test_block_dml_detects_delete():
    v = block_dml_writes("DELETE FROM customer")
    assert v is not None


def test_block_dml_allows_select():
    v = block_dml_writes("SELECT * FROM customer")
    assert v is None


# --- enforce_row_limit ---

def test_row_limit_appends_when_missing():
    sql, v = enforce_row_limit("SELECT * FROM customer", limit=1000)
    assert "LIMIT 1000" in sql.upper()
    assert v is None  # appending is not a violation


def test_row_limit_clamps_when_exceeds():
    sql, v = enforce_row_limit("SELECT * FROM customer LIMIT 5000", limit=1000)
    assert "LIMIT 1000" in sql.upper()
    assert "5000" not in sql
    assert v is not None
    assert "clamped" in v.reason.lower() or "reduced" in v.reason.lower()


def test_row_limit_respects_under_limit():
    sql, v = enforce_row_limit("SELECT * FROM customer LIMIT 50", limit=1000)
    assert "LIMIT 50" in sql.upper()
    assert v is None


def test_row_limit_keeps_existing_exact():
    sql, v = enforce_row_limit("SELECT * FROM customer LIMIT 1000", limit=1000)
    assert v is None


# --- check_subquery_depth ---

def test_subquery_depth_flat_passes():
    v = check_subquery_depth("SELECT * FROM customer", max_depth=3)
    assert v is None


def test_subquery_depth_one_level_passes():
    sql = "SELECT * FROM (SELECT * FROM customer) sub"
    v = check_subquery_depth(sql, max_depth=3)
    assert v is None


def test_subquery_depth_four_levels_fails():
    sql = (
        "SELECT * FROM ("
        "SELECT * FROM ("
        "SELECT * FROM ("
        "SELECT * FROM ("
        "SELECT * FROM customer"
        ") a) b) c) d"
    )
    v = check_subquery_depth(sql, max_depth=3)
    assert v is not None
    assert v.rule == "check_subquery_depth"
    assert "depth" in v.reason.lower()