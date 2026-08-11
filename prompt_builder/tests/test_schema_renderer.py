from schema_engine.models import ColumnInfo, ForeignKeyInfo, TableInfo, Schema
from prompt_builder.schema_renderer import render_schema_context


def test_renders_selected_table():
    col = ColumnInfo("customer_id", "integer", True, False, [1, 2])
    col2 = ColumnInfo("first_name", "varchar(45)", False, False, ["Mary"])
    fk = ForeignKeyInfo("address_id", "address", "address_id")
    table = TableInfo("customer", [col, col2], [fk], {"first_name": ["Mary", "John"]})
    schema = Schema(tables=[table])
    result = render_schema_context(schema, ["customer"])
    assert "customer" in result
    assert "customer_id" in result
    assert "first_name" in result
    assert "Mary" in result
    assert "address" in result


def test_omits_unselected_tables():
    film = TableInfo("film", [ColumnInfo("film_id", "integer", True, False)], [], {})
    customer = TableInfo("customer", [ColumnInfo("customer_id", "integer", True, False)], [], {})
    schema = Schema(tables=[film, customer])
    result = render_schema_context(schema, ["customer"])
    assert "customer" in result
    assert "film" not in result


def test_render_without_relevant_tables_renders_all():
    film = TableInfo("film", [ColumnInfo("film_id", "integer", True, False)], [], {})
    schema = Schema(tables=[film])
    result = render_schema_context(schema, [])
    assert "film" in result


def test_renders_sample_values():
    col = ColumnInfo("rating", "varchar(10)", False, False)
    table = TableInfo("film", [col], [], {"rating": ["PG", "R", "G"]})
    schema = Schema(tables=[table])
    result = render_schema_context(schema, ["film"])
    assert "PG" in result
    assert "R" in result
    assert "G" in result
