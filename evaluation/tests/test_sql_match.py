from evaluation.dataset import GoldenCase
from evaluation.metrics.sql_match import SqlMatchResult, evaluate, normalize_sql


def test_normalize_ignores_case_and_whitespace():
    a = "  SELECT email   FROM customer WHERE id=5 ; "
    b = "select email from customer where id = 5;"
    assert normalize_sql(a) == normalize_sql(b)


def test_normalize_ignores_trailing_semicolon():
    assert normalize_sql("SELECT 1;") == normalize_sql("SELECT 1")


def test_normalize_upper_cases_keywords_lower_cases_identifiers():
    n = normalize_sql("select EMAIL from CUSTOMER")
    assert n.startswith("SELECT email FROM customer")


def test_evaluate_exact_match_true():
    case = GoldenCase("x", "simple_lookup", "q", "SELECT email FROM customer;", 1, "")
    assert evaluate(case, _res("select email from customer;")) == SqlMatchResult("x", True, True)


def test_evaluate_exact_match_false():
    case = GoldenCase("x", "simple_lookup", "q", "SELECT email FROM customer;", 1, "")
    assert evaluate(case, _res("select first_name from customer;")) == SqlMatchResult("x", True, False)


def test_evaluate_ambiguous_matches_any_gold():
    case = GoldenCase("x", "ambiguous", "q", ["SELECT a;", "SELECT b;"], 1, "")
    assert evaluate(case, _res("select b;")) == SqlMatchResult("x", True, True)


def test_evaluate_unanswerable_not_applicable():
    case = GoldenCase("x", "unanswerable", "q", None, None, "")
    assert evaluate(case, _res("select 1;")) == SqlMatchResult("x", False, None)


class _SQLResult:
    def __init__(self, sql):
        self.sql = sql


def _res(sql):
    return type("R", (), {"generated_sql": _SQLResult(sql)})()
