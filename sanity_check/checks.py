from __future__ import annotations

from sanity_check.models import SanityAnomaly, SanityCheckResult
from sanity_check.stats import get_column_min_max, get_table_row_counts

NULL_THRESHOLD_CHECK = "null_heavy_columns"
COUNT_CHECK = "count_magnitude"
AGGREGATE_CHECK = "aggregate_range"
DATE_CHECK = "date_range"


def check_null_heavy_columns(result, null_threshold: float) -> SanityAnomaly | None:
    total = result.row_count
    if total == 0:
        return None
    for col in result.columns:
        nulls = sum(1 for row in result.data if row.get(col) is None)
        fraction = nulls / total
        if fraction > null_threshold:
            return SanityAnomaly(
                check=NULL_THRESHOLD_CHECK,
                severity="warning",
                message=(
                    f"Column '{col}' is {fraction:.0%} NULL, which may indicate a bad JOIN"
                ),
            )
    return None


def check_count_magnitude(result, tables: list[str], conn) -> SanityAnomaly | None:
    if not tables:
        return None
    counts = get_table_row_counts(conn, tables)
    if not counts:
        return None
    max_table_rows = max(counts.values())
    if result.row_count > max_table_rows:
        return SanityAnomaly(
            check=COUNT_CHECK,
            severity="error",
            message=(
                f"Result has {result.row_count} rows but the largest referenced table "
                f"has {max_table_rows} rows"
            ),
        )
    return None


def check_aggregate_range(result, tables: list[str], columns: list[str], conn) -> SanityAnomaly | None:
    if not tables or not columns:
        return None
    for col in columns:
        for table in tables:
            lo, hi = get_column_min_max(conn, table, col)
            if lo is None or hi is None:
                continue
            for row in result.data:
                value = row.get(col)
                if value is None:
                    continue
                try:
                    numeric = float(value)
                except (TypeError, ValueError):
                    continue
                if numeric < float(lo) or numeric > float(hi):
                    return SanityAnomaly(
                        check=AGGREGATE_CHECK,
                        severity="warning",
                        message=(
                            f"Aggregate '{col}' value {value} is outside the column "
                            f"range [{lo}, {hi}]"
                        ),
                    )
    return None


def check_date_range(result, tables: list[str], columns: list[str], conn) -> SanityAnomaly | None:
    if not tables or not columns:
        return None
    for col in columns:
        for table in tables:
            lo, hi = get_column_min_max(conn, table, col)
            if lo is None or hi is None:
                continue
            for row in result.data:
                value = row.get(col)
                if value is None or isinstance(value, (int, float)):
                    continue
                if value < lo or value > hi:
                    return SanityAnomaly(
                        check=DATE_CHECK,
                        severity="warning",
                        message=(
                            f"Date '{value}' in column '{col}' is outside the data "
                            f"timespan [{lo}, {hi}]"
                        ),
                    )
    return None


def run_checks(sql: str, result, tables: list[str], columns: list[str], conn, settings) -> SanityCheckResult:
    anomalies: list[SanityAnomaly] = []
    checks = [
        check_null_heavy_columns(result, settings.sanity_null_threshold),
        check_count_magnitude(result, tables, conn),
        check_aggregate_range(result, tables, columns, conn),
        check_date_range(result, tables, columns, conn),
    ]
    for anomaly in checks:
        if anomaly is not None:
            anomalies.append(anomaly)
    checks_run = len(checks)
    passed = checks_run - len(anomalies)
    pass_rate = passed / checks_run if checks_run else 1.0
    return SanityCheckResult(
        checks_run=checks_run,
        passed=passed,
        anomalies=anomalies,
        pass_rate=pass_rate,
    )
