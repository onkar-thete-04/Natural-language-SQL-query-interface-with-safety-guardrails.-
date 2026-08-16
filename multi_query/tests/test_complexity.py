from __future__ import annotations

from multi_query.complexity import is_complex
from sql_generator.models import SQLResult


def _sql_result(sql):
    return SQLResult(sql=sql, explanation="", confidence=0.9, tables=[], columns=[])


def test_join_sql_is_complex():
    assert is_complex("find customers with rentals", _sql_result("SELECT * FROM customer c JOIN rental r ON c.customer_id = r.customer_id;")) is True


def test_group_by_sql_is_complex():
    assert is_complex("count per category", _sql_result("SELECT category_id, COUNT(*) FROM film_category GROUP BY category_id;")) is True


def test_subquery_sql_is_complex():
    assert is_complex("who rented the most", _sql_result("SELECT * FROM customer WHERE customer_id IN (SELECT customer_id FROM rental);")) is True


def test_aggregation_question_is_complex():
    assert is_complex("how many films are there", _sql_result("SELECT COUNT(*) FROM film;")) is True


def test_simple_lookup_is_not_complex():
    assert is_complex("list all customers", _sql_result("SELECT * FROM customer;")) is False
