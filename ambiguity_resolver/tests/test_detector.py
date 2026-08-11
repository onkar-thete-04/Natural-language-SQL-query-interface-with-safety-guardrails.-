import numpy as np

from shared.models import Interpretation, ClarificationRequest
from schema_engine.models import ColumnInfo, TableInfo, Schema


class FakeEmbedder:
    def embed_single(self, text: str) -> list[float]:
        mapping = {
            "revenue": [1.0, 0.0, 0.0], "sales": [0.9, 0.1, 0.0],
            "earnings": [0.85, 0.1, 0.05], "income": [0.8, 0.15, 0.05],
            "turnover": [0.75, 0.2, 0.05],
            "active": [0.0, 1.0, 0.0], "current": [0.1, 0.85, 0.05],
            "open": [0.05, 0.9, 0.05], "ongoing": [0.1, 0.8, 0.1],
            "customer": [0.0, 0.0, 0.1],
        }
        return mapping.get(text.lower(), [0.0, 0.0, 0.0])

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_single(t) for t in texts]


def make_pagila_schema():
    customer = TableInfo("customer", [
        ColumnInfo("customer_id", "integer", True, False),
        ColumnInfo("first_name", "varchar(45)", False, False),
        ColumnInfo("active", "boolean", False, False),
    ], [], {})
    payment = TableInfo("payment", [
        ColumnInfo("payment_id", "integer", True, False),
        ColumnInfo("amount", "numeric", False, False),
    ], [], {})
    rental = TableInfo("rental", [
        ColumnInfo("rental_id", "integer", True, False),
        ColumnInfo("rental_date", "timestamp", False, False),
        ColumnInfo("return_date", "timestamp", False, True),
    ], [], {})
    return Schema(tables=[customer, payment, rental])


def test_detects_revenue_ambiguity():
    from ambiguity_resolver.detector import AmbiguityDetector
    detector = AmbiguityDetector(FakeEmbedder(), make_pagila_schema())
    result = detector.detect("which store generated the most revenue")
    assert result is not None
    assert len(result.interpretations) >= 1
    assert result.interpretations[0].label == "Gross Revenue"


def test_no_ambiguity_for_unambiguous_question():
    from ambiguity_resolver.detector import AmbiguityDetector
    detector = AmbiguityDetector(FakeEmbedder(), make_pagila_schema())
    result = detector.detect("find customer by id")
    assert result is None


def test_interpretation_has_constraint_field():
    from ambiguity_resolver.detector import AmbiguityDetector
    detector = AmbiguityDetector(FakeEmbedder(), make_pagila_schema())
    result = detector.detect("what are the total earnings")
    assert result is not None
    interp = result.interpretations[0]
    assert interp.constraint
    assert "payment.amount" in interp.constraint.lower()
