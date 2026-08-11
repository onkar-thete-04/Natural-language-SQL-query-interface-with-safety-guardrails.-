from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ColumnInfo:
    name: str
    data_type: str
    is_primary_key: bool = False
    is_nullable: bool = True
    sample_values: list[str | int | float] = field(default_factory=list)

    @property
    def description_text(self) -> str:
        pk = " (PK)" if self.is_primary_key else ""
        return f"{self.name} ({self.data_type}){pk}"


@dataclass(frozen=True)
class ForeignKeyInfo:
    column_name: str
    referenced_table: str
    referenced_column: str


@dataclass(frozen=True)
class TableInfo:
    name: str
    columns: list[ColumnInfo] = field(default_factory=list)
    foreign_keys: list[ForeignKeyInfo] = field(default_factory=list)
    sample_values: dict[str, list[str | int | float]] = field(default_factory=dict)

    @property
    def description_text(self) -> str:
        col_descs = ", ".join(c.description_text for c in self.columns)
        return f"{self.name}: {col_descs}"


@dataclass(frozen=True)
class Schema:
    tables: list[TableInfo] = field(default_factory=list)

    def get_table(self, name: str) -> TableInfo | None:
        name_lower = name.lower()
        for table in self.tables:
            if table.name.lower() == name_lower:
                return table
        return None
