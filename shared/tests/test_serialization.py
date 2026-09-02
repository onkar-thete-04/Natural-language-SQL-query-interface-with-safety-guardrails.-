from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from shared.serialization import to_dict


@dataclass(frozen=True)
class _Inner:
    x: int


@dataclass(frozen=True)
class _Outer:
    name: str
    inner: _Inner
    values: list[_Inner]
    pair: tuple[int, int]
    maybe: _Inner | None


@dataclass(frozen=True)
class _DbRow:
    amount: Decimal
    ts: datetime
    day: date
    id: UUID


def test_to_dict_recurses_dataclasses():
    obj = _Outer(
        name="a",
        inner=_Inner(1),
        values=[_Inner(2), _Inner(3)],
        pair=(4, 5),
        maybe=None,
    )
    assert to_dict(obj) == {
        "name": "a",
        "inner": {"x": 1},
        "values": [{"x": 2}, {"x": 3}],
        "pair": [4, 5],
        "maybe": None,
    }


def test_to_dict_passes_through_primitives():
    assert to_dict("s") == "s"
    assert to_dict(1) == 1
    assert to_dict(1.5) == 1.5
    assert to_dict(True) is True
    assert to_dict(None) is None


def test_to_dict_converts_dict_keys_to_strings():
    assert to_dict({1: "a"}) == {"1": "a"}


def test_to_dict_converts_db_value_types():
    row_id = uuid4()
    obj = _DbRow(
        amount=Decimal("3.14"),
        ts=datetime(2026, 9, 1, 12, 30, 45),
        day=date(2026, 9, 1),
        id=row_id,
    )
    assert to_dict(obj) == {
        "amount": 3.14,
        "ts": "2026-09-01T12:30:45",
        "day": "2026-09-01",
        "id": str(row_id),
    }
