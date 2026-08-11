from schema_engine.models import ColumnInfo, ForeignKeyInfo, TableInfo, Schema


def test_column_info_creation():
    col = ColumnInfo(name="customer_id", data_type="integer", is_primary_key=True, is_nullable=False, sample_values=[1, 2, 3])
    assert col.name == "customer_id"
    assert col.data_type == "integer"
    assert col.is_primary_key is True
    assert col.is_nullable is False
    assert col.sample_values == [1, 2, 3]


def test_column_description_text():
    col = ColumnInfo(name="email", data_type="varchar(50)", is_primary_key=False, is_nullable=True, sample_values=["a@b.com"])
    assert col.description_text == "email (varchar(50))"


def test_foreign_key_info():
    fk = ForeignKeyInfo(column_name="address_id", referenced_table="address", referenced_column="address_id")
    assert fk.column_name == "address_id"
    assert fk.referenced_table == "address"
    assert fk.referenced_column == "address_id"


def test_table_info_description_text():
    cols = [
        ColumnInfo("customer_id", "integer", True, False, [1]),
        ColumnInfo("first_name", "varchar(45)", False, False, ["Mary"]),
    ]
    table = TableInfo(name="customer", columns=cols, foreign_keys=[], sample_values={"first_name": ["Mary", "John"]})
    desc = table.description_text
    assert "customer" in desc
    assert "customer_id" in desc
    assert "first_name" in desc


def test_schema_get_table():
    table = TableInfo("customer", [], [], {})
    schema = Schema(tables=[table])
    assert schema.get_table("customer") is table
    assert schema.get_table("nonexistent") is None


def test_schema_get_table_case_insensitive():
    table = TableInfo("Customer", [], [], {})
    schema = Schema(tables=[table])
    assert schema.get_table("customer") is table
    assert schema.get_table("CUSTOMER") is table
