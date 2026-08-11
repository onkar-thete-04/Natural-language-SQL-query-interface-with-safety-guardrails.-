from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from schema_engine.models import Schema, TableInfo

CATEGORICAL_TYPES = {"varchar", "character varying", "char", "text", "boolean", "enum"}


def _is_categorical(data_type: str) -> bool:
    lower = data_type.lower()
    for ct in CATEGORICAL_TYPES:
        if lower.startswith(ct):
            return True
    return False


def sample_categorical_values(engine: Engine, table_name: str, column_name: str, limit: int = 5) -> list:
    try:
        with engine.connect() as conn:
            result = conn.execute(
                sa.text(f'SELECT DISTINCT "{column_name}" FROM "{table_name}" WHERE "{column_name}" IS NOT NULL LIMIT {limit}')
            )
            return [row[0] for row in result.fetchall()]
    except SQLAlchemyError:
        return []


def enrich_schema_with_samples(schema: Schema, engine: Engine, limit: int = 5) -> Schema:
    enriched_tables: list[TableInfo] = []
    for table in schema.tables:
        sample_values: dict = {}
        for col in table.columns:
            if _is_categorical(col.data_type):
                samples = sample_categorical_values(engine, table.name, col.name, limit=limit)
                if samples:
                    sample_values[col.name] = samples
        enriched_tables.append(TableInfo(
            name=table.name,
            columns=list(table.columns),
            foreign_keys=list(table.foreign_keys),
            sample_values=sample_values,
        ))
    return Schema(tables=enriched_tables)
