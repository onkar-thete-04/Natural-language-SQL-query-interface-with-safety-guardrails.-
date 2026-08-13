from __future__ import annotations

from shared.text_similarity import cosine_similarity


def test_cosine_identical_vectors_is_one():
    assert cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 1.0


def test_cosine_orthogonal_vectors_is_zero():
    result = cosine_similarity([1.0, 0.0], [0.0, 1.0])
    assert abs(result) < 1e-6


def test_cosine_zero_vector_returns_zero():
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_cosine_opposite_vectors_is_negative_one():
    assert cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == -1.0
