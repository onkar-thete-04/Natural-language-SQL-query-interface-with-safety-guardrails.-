from __future__ import annotations

from schema_engine.models import Schema


def render_schema_context(schema: Schema, relevant_tables: list[str]) -> str:
    if not relevant_tables:
        tables_to_render = list(schema.tables)
    else:
        relevant_lower = {t.lower() for t in relevant_tables}
        tables_to_render = [t for t in schema.tables if t.name.lower() in relevant_lower]

    lines: list[str] = []
    for table in tables_to_render:
        lines.append(f"Table: {table.name}")
        for col in table.columns:
            pk_marker = " (PK)" if col.is_primary_key else ""
            nullable = " NULL" if col.is_nullable else " NOT NULL"
            lines.append(f"  - {col.name}: {col.data_type}{pk_marker}{nullable}")
        if table.foreign_keys:
            lines.append("  Foreign Keys:")
            for fk in table.foreign_keys:
                lines.append(f"    {fk.column_name} -> {fk.referenced_table}({fk.referenced_column})")
        if table.sample_values:
            lines.append("  Sample Values:")
            for col_name, samples in table.sample_values.items():
                sample_str = ", ".join(str(s) for s in samples)
                lines.append(f"    {col_name}: {sample_str}")
        lines.append("")
    return "\n".join(lines).strip()
