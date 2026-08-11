import pytest
from sqlalchemy import create_engine, text

from schema_engine.introspector import SchemaIntrospector
from schema_engine.models import ColumnInfo, ForeignKeyInfo, Schema, TableInfo
from shared.errors import SchemaIntrospectionError


def test_introspector_returns_schema():
    introspector = SchemaIntrospector("sqlite:///:memory:")
    schema = introspector.introspect()
    assert isinstance(schema, Schema)
    assert schema.tables == []


def test_introspector_discovers_table_with_columns(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE customer (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"))
        conn.commit()

    introspector = SchemaIntrospector(f"sqlite:///{db_path}")
    schema = introspector.introspect()

    assert len(schema.tables) == 1
    table = schema.tables[0]
    assert table.name == "customer"
    assert len(table.columns) == 2

    id_col = next(c for c in table.columns if c.name == "id")
    assert id_col.data_type == "INTEGER"
    assert id_col.is_primary_key is True
    assert id_col.is_nullable is True

    name_col = next(c for c in table.columns if c.name == "name")
    assert name_col.data_type == "TEXT"
    assert name_col.is_primary_key is False
    assert name_col.is_nullable is False


def test_introspector_discovers_foreign_keys(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE address (address_id INTEGER PRIMARY KEY, city TEXT)"))
        conn.execute(text(
            "CREATE TABLE customer (id INTEGER PRIMARY KEY, "
            "address_id INTEGER REFERENCES address(address_id))"
        ))
        conn.commit()

    introspector = SchemaIntrospector(f"sqlite:///{db_path}")
    schema = introspector.introspect()

    customer = schema.get_table("customer")
    assert customer is not None
    assert len(customer.foreign_keys) == 1
    fk = customer.foreign_keys[0]
    assert fk.column_name == "address_id"
    assert fk.referenced_table == "address"
    assert fk.referenced_column == "address_id"


def test_introspector_raises_on_connection_failure():
    introspector = SchemaIntrospector("sqlite:///nonexistent/path/that/should/not/exist.db")
    with pytest.raises(SchemaIntrospectionError, match="Failed to connect to database"):
        introspector.introspect()


def test_introspector_discovers_multiple_tables(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE t1 (a INTEGER)"))
        conn.execute(text("CREATE TABLE t2 (b TEXT)"))
        conn.commit()

    introspector = SchemaIntrospector(f"sqlite:///{db_path}")
    schema = introspector.introspect()

    table_names = {t.name for t in schema.tables}
    assert table_names == {"t1", "t2"}


def test_introspector_handles_composite_primary_keys(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE t (a INTEGER, b INTEGER, PRIMARY KEY (a, b))"))
        conn.commit()

    introspector = SchemaIntrospector(f"sqlite:///{db_path}")
    schema = introspector.introspect()

    table = schema.tables[0]
    pk_cols = [c for c in table.columns if c.is_primary_key]
    assert len(pk_cols) == 2
    assert {c.name for c in pk_cols} == {"a", "b"}
