import numpy as np

from schema_engine.models import ColumnInfo, ForeignKeyInfo, TableInfo, Schema


class FakeEmbedder:
    def __init__(self):
        self.embed_calls: list[list[str]] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.embed_calls.append(texts)
        vectors = []
        for t in texts:
            if "customer" in t.lower():
                vectors.append([1.0, 0.0, 0.0])
            elif "film" in t.lower():
                vectors.append([0.0, 0.0, 0.0])
            elif "rental" in t.lower():
                vectors.append([0.5, 0.0, 0.0])
            else:
                vectors.append([0.0, 0.0, 0.0])
        return vectors

    def embed_single(self, text: str) -> list[float]:
        return self.embed([text])[0]


def make_test_schema():
    customer = TableInfo("customer", [
        ColumnInfo("customer_id", "integer", True, False),
        ColumnInfo("first_name", "varchar(45)", False, False),
        ColumnInfo("address_id", "integer", False, False),
    ], [ForeignKeyInfo("address_id", "address", "address_id")], {})

    film = TableInfo("film", [ColumnInfo("film_id", "integer", True, False)], [], {})
    rental = TableInfo("rental", [ColumnInfo("rental_id", "integer", True, False)], [], {})
    address = TableInfo("address", [ColumnInfo("address_id", "integer", True, False)], [], {})

    return Schema(tables=[customer, film, rental, address])


def test_scorer_returns_tables_above_threshold():
    from relevance_filter.scorer import RelevanceScorer
    scorer = RelevanceScorer(FakeEmbedder(), make_test_schema(), threshold=0.3)
    result = scorer.score_tables("find customer emails")
    assert "customer" in result


def test_scorer_includes_fk_connected_tables():
    from relevance_filter.scorer import RelevanceScorer
    scorer = RelevanceScorer(FakeEmbedder(), make_test_schema(), threshold=0.3)
    result = scorer.score_tables("find customer emails")
    assert "address" in result


def test_scorer_excludes_below_threshold():
    from relevance_filter.scorer import RelevanceScorer
    scorer = RelevanceScorer(FakeEmbedder(), make_test_schema(), threshold=0.3)
    result = scorer.score_tables("find customer emails")
    assert "film" not in result


def test_scorer_returns_empty_for_no_match():
    from relevance_filter.scorer import RelevanceScorer
    scorer = RelevanceScorer(FakeEmbedder(), make_test_schema(), threshold=0.9)
    result = scorer.score_tables("completely unrelated topic")
    assert result == []
