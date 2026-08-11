import sqlalchemy as sa
from sqlalchemy import create_engine

from schema_engine.sampler import sample_categorical_values, enrich_schema_with_samples
from schema_engine.models import ColumnInfo, TableInfo, Schema


def test_sample_returns_distinct_values():
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        conn.execute(sa.text("CREATE TABLE t (name TEXT)"))
        conn.execute(sa.text("INSERT INTO t VALUES ('Alice')"))
        conn.execute(sa.text("INSERT INTO t VALUES ('Bob')"))
        conn.execute(sa.text("INSERT INTO t VALUES ('Alice')"))
        conn.commit()
    result = sample_categorical_values(engine, "t", "name", limit=5)
    assert sorted(result) == ["Alice", "Bob"]


def test_sample_respects_limit():
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        conn.execute(sa.text("CREATE TABLE t (name TEXT)"))
        for i in range(10):
            conn.execute(sa.text(f"INSERT INTO t VALUES ('val_{i}')"))
        conn.commit()
    result = sample_categorical_values(engine, "t", "name", limit=3)
    assert len(result) == 3


def test_sample_handles_empty_table():
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        conn.execute(sa.text("CREATE TABLE t (name TEXT)"))
        conn.commit()
    result = sample_categorical_values(engine, "t", "name", limit=5)
    assert result == []


def test_enrich_schema_with_samples():
    col = ColumnInfo(name="first_name", data_type="varchar(45)", is_primary_key=False, is_nullable=False)
    table = TableInfo(name="customer", columns=[col], foreign_keys=[])
    schema = Schema(tables=[table])

    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        conn.execute(sa.text("CREATE TABLE customer (first_name TEXT)"))
        conn.execute(sa.text("INSERT INTO customer VALUES ('Mary')"))
        conn.execute(sa.text("INSERT INTO customer VALUES ('John')"))
        conn.commit()

    enriched = enrich_schema_with_samples(schema, engine, limit=5)
    customer_table = enriched.get_table("customer")
    assert customer_table is not None
    assert "first_name" in customer_table.sample_values
    assert "Mary" in customer_table.sample_values["first_name"]
