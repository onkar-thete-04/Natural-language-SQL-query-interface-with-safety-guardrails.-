from __future__ import annotations

from sqlalchemy import text


def get_table_row_counts(conn, tables: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table in tables:
        try:
            result = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"')).fetchone()
            counts[table.lower()] = int(result[0])
        except Exception:
            counts[table.lower()] = 0
    return counts


def get_column_min_max(conn, table: str, column: str) -> tuple[object | None, object | None]:
    try:
        row = conn.execute(
            text(f'SELECT MIN("{column}"), MAX("{column}") FROM "{table}"')
        ).fetchone()
        return row[0], row[1]
    except Exception:
        return None, None
