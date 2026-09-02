from evaluation.metrics.hallucination import classify, compute_rate, is_flagged
from evaluation.metrics.execution_match import ExecutionMatchResult


def _result(aligned=True, anomalies=(), overall=90.0, clarification=None):
    return type("R", (), {
        "alignment": None if aligned is None else type("A", (), {"aligned": aligned})(),
        "sanity": None if not anomalies else type("S", (), {"anomalies": list(anomalies)})(),
        "confidence_report": type("C", (), {"overall": overall})(),
        "clarification": clarification,
    })()


def test_flagged_when_alignment_low():
    assert is_flagged(_result(aligned=False), 60.0) is True


def test_flagged_when_sanity_anomaly():
    assert is_flagged(_result(anomalies=["x"]), 60.0) is True


def test_flagged_when_low_confidence():
    assert is_flagged(_result(overall=50.0), 60.0) is True


def test_flagged_when_clarification():
    assert is_flagged(_result(clarification="clarify me"), 60.0) is True


def test_not_flagged_when_clean():
    assert is_flagged(_result(), 60.0) is False


def test_classify_bad_when_execution_mismatch():
    exec_match = ExecutionMatchResult("x", True, False, "diverged")
    r = classify("x", _result(), exec_match, 60.0)
    assert r.is_bad is True and r.flagged is False


def test_compute_rate_recall_and_precision():
    results = [
        classify("1", _result(aligned=False), ExecutionMatchResult("1", True, False, "bad"), 60.0),  # bad+flagged
        classify("2", _result(), ExecutionMatchResult("2", True, False, "bad"), 60.0),               # bad not flagged
        classify("3", _result(), ExecutionMatchResult("3", True, True, ""), 60.0),                    # good
    ]
    rate = compute_rate(results)
    assert rate["recall"] == 0.5
    assert rate["precision"] == 1.0


def test_compute_rate_none_when_no_bad():
    results = [classify("1", _result(), ExecutionMatchResult("1", True, True, ""), 60.0)]
    rate = compute_rate(results)
    assert rate["recall"] is None and rate["precision"] is None
