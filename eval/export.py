from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import yaml


def export_incorrect(question: str, sql: str, note: str, path: str) -> None:
    cases = _load_yaml(path).get("test_cases", []) or []
    cases.append({
        "id": uuid.uuid4().hex,
        "question": question,
        "generated_sql": sql,
        "gold_sql": None,
        "note": note,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    _write_yaml(path, {"test_cases": cases})


def export_correct(question: str, sql: str, tables: list[str], path: str) -> None:
    data = _load_yaml(path)
    domains = data.setdefault("domains", {})
    entries = domains.setdefault("user_feedback", [])
    entries.append({
        "question": question,
        "sql": sql,
        "pattern": "user_corrected",
        "tables": list(tables),
    })
    _write_yaml(path, data)


def _load_yaml(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


def _write_yaml(path: str, data: dict) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)
    os.replace(tmp, path)
