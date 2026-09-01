from __future__ import annotations

import json

from store.repository import Store


def _store():
    return Store(":memory:")


def test_save_and_get_history():
    s = _store()
    s.save_query(
        query_id="q1", session_id="s1", question="how many films", sql="SELECT COUNT(*) FROM film;",
        confidence=90.0, result_json={"generated_sql": {"sql": "SELECT COUNT(*) FROM film;"}},
        created_at="2026-09-01T00:00:00+00:00",
    )
    history = s.get_history("s1")
    assert len(history) == 1
    assert history[0]["query_id"] == "q1"
    assert history[0]["sql"] == "SELECT COUNT(*) FROM film;"
    assert history[0]["rating"] is None


def test_history_filters_by_session():
    s = _store()
    s.save_query(query_id="q1", session_id="a", question="q", sql="SELECT 1;",
                 confidence=1.0, result_json={}, created_at="2026-09-01T00:00:00+00:00")
    s.save_query(query_id="q2", session_id="b", question="q", sql="SELECT 2;",
                 confidence=1.0, result_json={}, created_at="2026-09-01T00:00:00+00:00")
    assert len(s.get_history("a")) == 1
    assert s.get_history("a")[0]["query_id"] == "q1"


def test_get_query_roundtrips_json():
    s = _store()
    payload = {"generated_sql": {"sql": "SELECT 1;"}, "question": "q"}
    s.save_query(query_id="q1", session_id="s1", question="q", sql="SELECT 1;",
                 confidence=1.0, result_json=payload, created_at="2026-09-01T00:00:00+00:00")
    assert s.get_query("q1") == payload
    assert s.get_query("missing") is None


def test_save_and_get_feedback():
    s = _store()
    s.save_query(query_id="q1", session_id="s1", question="q", sql="SELECT 1;",
                 confidence=1.0, result_json={}, created_at="2026-09-01T00:00:00+00:00")
    s.save_feedback(query_id="q1", rating="correct", note="looks right",
                    created_at="2026-09-01T00:00:00+00:00")
    fb = s.get_feedback("q1")
    assert fb["rating"] == "correct"
    assert s.get_history("s1")[0]["rating"] == "correct"


def test_save_feedback_replaces_previous():
    s = _store()
    s.save_query(query_id="q1", session_id="s1", question="q", sql="SELECT 1;",
                 confidence=1.0, result_json={}, created_at="2026-09-01T00:00:00+00:00")
    s.save_feedback(query_id="q1", rating="correct", note="", created_at="t1")
    s.save_feedback(query_id="q1", rating="incorrect", note="", created_at="t2")
    assert s.get_feedback("q1")["rating"] == "incorrect"
