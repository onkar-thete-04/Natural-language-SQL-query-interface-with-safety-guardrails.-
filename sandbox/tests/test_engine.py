from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch, call

import pytest

from sandbox.engine import create_readonly_engine, read_only_session


def test_create_readonly_engine_returns_engine():
    with patch("sandbox.engine.create_engine") as mock_create:
        mock_engine = MagicMock()
        mock_create.return_value = mock_engine
        result = create_readonly_engine("postgresql://readonly_user:readonly_pass@localhost:5432/pagila")
        assert result is mock_engine
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["isolation_level"] == "SERIALIZABLE"
        assert call_kwargs["execution_options"]["read_only"] is True


def _setup_engine():
    engine = MagicMock()
    conn = MagicMock()
    engine.connect.return_value.__enter__.return_value = conn
    engine.connect.return_value.__exit__.return_value = False
    return engine, conn


def test_read_only_session_yields_connection():
    engine, conn = _setup_engine()
    with read_only_session(engine) as c:
        assert c is conn
    assert conn.execute.call_count == 2
    assert "BEGIN READ ONLY" in conn.execute.call_args_list[0].args[0].text
    assert "ROLLBACK" in conn.execute.call_args_list[1].args[0].text


def test_read_only_session_rolls_back_on_exception():
    engine, conn = _setup_engine()
    with pytest.raises(ValueError, match="boom"):
        with read_only_session(engine):
            raise ValueError("boom")
    assert "ROLLBACK" in conn.execute.call_args_list[-1].args[0].text