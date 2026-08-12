from __future__ import annotations

import pytest

from shared.errors import (
    TextToSQLError,
    SchemaIntrospectionError,
    LLMClientError,
    SQLValidationError,
    GuardrailError,
    ExecutionError,
)


def test_text_to_sql_error_is_base():
    assert issubclass(TextToSQLError, Exception)


def test_existing_errors_still_subclass_exception():
    assert issubclass(SchemaIntrospectionError, Exception)
    assert issubclass(LLMClientError, Exception)


def test_new_errors_subclass_text_to_sql_error():
    assert issubclass(SQLValidationError, TextToSQLError)
    assert issubclass(GuardrailError, TextToSQLError)
    assert issubclass(ExecutionError, TextToSQLError)


def test_errors_are_raisable():
    with pytest.raises(SQLValidationError, match="bad sql"):
        raise SQLValidationError("bad sql")
    with pytest.raises(GuardrailError, match="blocked"):
        raise GuardrailError("blocked")
    with pytest.raises(ExecutionError, match="boom"):
        raise ExecutionError("boom")
