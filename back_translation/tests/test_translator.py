from __future__ import annotations

from unittest.mock import MagicMock

from back_translation.translator import back_translate


def test_back_translate_uses_judge_model_and_strips():
    client = MagicMock()
    client.generate_sql.return_value = "  What is the email of Mary Smith?  \n"
    settings = MagicMock()
    settings.judge_model = "judge-model"

    question = back_translate("SELECT email FROM customer;", client, settings)

    assert question == "What is the email of Mary Smith?"
    client.generate_sql.assert_called_once()
    args, kwargs = client.generate_sql.call_args
    assert kwargs["model"] == "judge-model"
    assert "SELECT email FROM customer;" in args[0]
