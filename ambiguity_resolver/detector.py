from __future__ import annotations

import numpy as np

from relevance_filter.embedder import SchemaEmbedder
from schema_engine.models import Schema
from shared.models import Interpretation, ClarificationRequest


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    arr_a = np.array(a, dtype=np.float32)
    arr_b = np.array(b, dtype=np.float32)
    norm_a = np.linalg.norm(arr_a)
    norm_b = np.linalg.norm(arr_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(arr_a, arr_b) / (norm_a * norm_b))


REVENUE_CLUSTER = ["revenue", "sales", "earnings", "income", "turnover"]
ACTIVE_CLUSTER = ["active", "current", "open", "ongoing"]
DATE_RECENT_CLUSTER = ["recent", "latest", "this month", "past 30 days", "last month"]
CLUSTER_THRESHOLD = 0.75


class AmbiguityDetector:
    def __init__(self, embedder: SchemaEmbedder, schema: Schema) -> None:
        self._embedder = embedder
        self._schema = schema
        self._cluster_centroids: dict[str, list[float]] = {}
        self._precompute_clusters()

    def _precompute_clusters(self) -> None:
        clusters = {"revenue": REVENUE_CLUSTER, "active": ACTIVE_CLUSTER, "date_recent": DATE_RECENT_CLUSTER}
        for cluster_name, terms in clusters.items():
            embeddings = self._embedder.embed(terms)
            centroid = np.mean(embeddings, axis=0).tolist()
            self._cluster_centroids[cluster_name] = centroid

    def detect(self, question: str) -> ClarificationRequest | None:
        words = question.lower().split()
        words = [w.strip(",.?;:!\"'") for w in words]
        words = [w for w in words if len(w) > 2]
        interpretations: list[Interpretation] = []
        matched = self._match_clusters(words)
        if "revenue" in matched:
            interpretations.extend(self._build_revenue_interpretations())
        if "active" in matched:
            interpretations.extend(self._build_active_interpretations())
        if "date_recent" in matched:
            interpretations.extend(self._build_date_interpretations())
        if not interpretations:
            return None
        return ClarificationRequest(original_question=question, interpretations=interpretations)

    def _match_clusters(self, words: list[str]) -> list[str]:
        matched: list[str] = []
        for word in words:
            word_embedding = self._embedder.embed_single(word)
            for cluster_name, centroid in self._cluster_centroids.items():
                if _cosine_similarity(word_embedding, centroid) >= CLUSTER_THRESHOLD:
                    matched.append(cluster_name)
                    break
        return matched

    def _has_column(self, table_name: str, column_name: str) -> bool:
        table = self._schema.get_table(table_name)
        if table is None:
            return False
        return any(c.name.lower() == column_name.lower() for c in table.columns)

    def _build_revenue_interpretations(self) -> list[Interpretation]:
        if not self._has_column("payment", "amount"):
            return []
        return [Interpretation(
            label="Gross Revenue",
            description="Total payments before subtracting refunds or adjustments",
            example_query="Find total revenue by store from payments",
            constraint="Use payment.amount AS revenue. Do not subtract refunds or adjustments.",
        )]

    def _build_active_interpretations(self) -> list[Interpretation]:
        has_customer_active = self._has_column("customer", "active")
        has_rental_dates = self._has_column("rental", "rental_date") and self._has_column("rental", "return_date")
        if not (has_customer_active and has_rental_dates):
            return []
        return [
            Interpretation(label="Active by Status", description="Customers where the active flag is TRUE",
                example_query="Find customers whose active status is TRUE",
                constraint="Use customer.active = TRUE to determine active customers."),
            Interpretation(label="Active by Rentals", description="Customers with currently unreturned rentals",
                example_query="Find customers with rentals where return_date IS NULL",
                constraint="Use rental.return_date IS NULL to determine currently active rentals."),
        ]

    def _build_date_interpretations(self) -> list[Interpretation]:
        return [
            Interpretation(label="Calendar Month", description="The most recent complete calendar month",
                example_query="How many rentals were made last calendar month?",
                constraint="Interpret the date range as the most recent complete calendar month."),
            Interpretation(label="Rolling 30 Days", description="The last 30 days from today",
                example_query="How many rentals were made in the last 30 days?",
                constraint="Interpret the date range as the last 30 days from the current date."),
        ]
