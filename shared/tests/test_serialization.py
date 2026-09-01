from __future__ import annotations

from dataclasses import dataclass

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
