from __future__ import annotations

from unittest.mock import MagicMock

from back_translation.models import AlignmentResult
from confidence.models import ConfidenceReport
from confidence.scorer import compute_confidence, compute_schema_coverage
from multi_query.models import AgreementResult
from sanity_check.models import SanityCheckResult
from schema_engine.models import ColumnInfo, Schema, TableInfo


def _settings():
    s = MagicMock()
    s.confidence_weight_syntax = 0.10
    s.confidence_weight_alignment = 0.30
    s.confidence_weight_sanity = 0.25
    s.confidence_weight_agreement = 0.20
    s.confidence_weight_coverage = 0.15
    return s


def _alignment(score=0.9):
    return AlignmentResult(
        back_translated_question="q", alignment_score=score,
        method="embedding", judge_rationale=None, aligned=True, low_confidence=False,
    )


def _sanity(pass_rate=1.0):
    return SanityCheckResult(checks_run=4, passed=4, anomalies=[], pass_rate=pass_rate)


def _agreement(agreed=True):
    return AgreementResult(agreed=agreed, identical=True, row_counts=(5, 5), divergence_detail=None)


def test_all_signals_high_yields_high_confidence():
    report = compute_confidence(
        syntax_score=1.0,
        alignment=_alignment(1.0),
        sanity=_sanity(1.0),
        agreement=_agreement(True),
        coverage=1.0,
        flags=[],
        settings=_settings(),
    )
    assert isinstance(report, ConfidenceReport)
    assert report.overall == 100.0


def test_unavailable_signals_renormalize():
    report = compute_confidence(
        syntax_score=1.0,
        alignment=None,
        sanity=_sanity(1.0),
        agreement=None,
        coverage=1.0,
        flags=[],
        settings=_settings(),
    )
    assert 90.0 <= report.overall <= 100.0


def test_diverged_agreement_lowers_score():
    high = compute_confidence(1.0, _alignment(0.95), _sanity(1.0), _agreement(True), 1.0, [], _settings())
    low = compute_confidence(1.0, _alignment(0.95), _sanity(1.0), _agreement(False), 1.0, [], _settings())
    assert low.overall < high.overall


def test_schema_coverage_full_match():
    schema = Schema(tables=[TableInfo(name="customer", columns=[ColumnInfo(name="email", data_type="varchar")])])
    coverage, flags = compute_schema_coverage(["customer"], ["email"], ["customer"], schema)
    assert coverage == 1.0
    assert flags == []


def test_schema_coverage_off_topic_table_flagged():
    schema = Schema(tables=[TableInfo(name="customer", columns=[ColumnInfo(name="email", data_type="varchar")])])
    coverage, flags = compute_schema_coverage(["customer", "store"], ["email"], ["customer"], schema)
    assert coverage == 0.5
    assert any("store" in f for f in flags)
