from __future__ import annotations

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from schema_engine.models import ColumnInfo, ForeignKeyInfo, TableInfo, Schema
from shared.errors import SchemaIntrospectionError


class SchemaIntrospector:
    def __init__(self, db_url: str) -> None:
        self._db_url = db_url

    def introspect(self) -> Schema:
        try:
            engine = create_engine(self._db_url)
            inspector = inspect(engine)
            table_names = inspector.get_table_names()
        except SQLAlchemyError as exc:
            raise SchemaIntrospectionError(f"Failed to connect to database: {exc}") from exc

        tables: list[TableInfo] = []
        for name in table_names:
            tables.append(self._build_table_info(inspector, name))
        return Schema(tables=tables)

    def _build_table_info(self, inspector, table_name: str) -> TableInfo:
        pk_constraint = inspector.get_pk_constraint(table_name)
        pk_columns: set[str] = set(pk_constraint.get("constrained_columns", []) or [])

        columns: list[ColumnInfo] = []
        for col in inspector.get_columns(table_name):
            columns.append(ColumnInfo(
                name=col["name"],
                data_type=str(col["type"]),
                is_primary_key=col["name"] in pk_columns,
                is_nullable=col.get("nullable", True),
            ))

        foreign_keys: list[ForeignKeyInfo] = []
        for fk in inspector.get_foreign_keys(table_name):
            constrained = fk.get("constrained_columns", []) or []
            referred = fk.get("referred_columns", []) or []
            for local_col, ref_col in zip(constrained, referred):
                foreign_keys.append(ForeignKeyInfo(
                    column_name=local_col,
                    referenced_table=fk["referred_table"],
                    referenced_column=ref_col,
                ))

        return TableInfo(name=table_name, columns=columns, foreign_keys=foreign_keys)
