from __future__ import annotations

import numpy as np

from relevance_filter.embedder import SchemaEmbedder
from schema_engine.models import Schema


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    arr_a = np.array(a, dtype=np.float32)
    arr_b = np.array(b, dtype=np.float32)
    norm_a = np.linalg.norm(arr_a)
    norm_b = np.linalg.norm(arr_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(arr_a, arr_b) / (norm_a * norm_b))


class RelevanceScorer:
    def __init__(self, embedder: SchemaEmbedder, schema: Schema, threshold: float = 0.3) -> None:
        self._embedder = embedder
        self._schema = schema
        self._threshold = threshold
        self._table_embeddings: dict[str, list[float]] = {}
        self._precompute()

    def _precompute(self) -> None:
        if not self._schema.tables:
            return
        descriptions = [t.description_text for t in self._schema.tables]
        embeddings = self._embedder.embed(descriptions)
        for table, emb in zip(self._schema.tables, embeddings):
            self._table_embeddings[table.name.lower()] = emb

    def score_tables(self, question: str) -> list[str]:
        if not self._schema.tables:
            return []
        question_embedding = self._embedder.embed_single(question)
        selected: set[str] = set()
        for table in self._schema.tables:
            table_emb = self._table_embeddings.get(table.name.lower())
            if table_emb is None:
                continue
            if _cosine_similarity(question_embedding, table_emb) >= self._threshold:
                selected.add(table.name.lower())
        if not selected:
            return []
        for table in self._schema.tables:
            if table.name.lower() not in selected:
                continue
            for fk in table.foreign_keys:
                selected.add(fk.referenced_table.lower())
        return sorted(selected)
