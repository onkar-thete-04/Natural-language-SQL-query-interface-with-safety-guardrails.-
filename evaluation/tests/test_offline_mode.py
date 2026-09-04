import pytest

from shared.config import Settings


def test_offline_mode_skips_api_key_check(monkeypatch):
    monkeypatch.setenv("OFFLINE_MODE", "true")
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    s = Settings()
    assert s.sql_gen_model
    assert s.nvidia_api_key == ""


def test_missing_api_key_raises_without_offline_mode(monkeypatch):
    monkeypatch.delenv("OFFLINE_MODE", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    with pytest.raises(ValueError):
        Settings()
