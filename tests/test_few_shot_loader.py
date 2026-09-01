from __future__ import annotations

import yaml

from few_shot_loader import FewShotLoader


def test_loader_merges_feedback_file(tmp_path):
    feedback = tmp_path / "feedback.yaml"
    feedback.write_text(
        yaml.safe_dump({
            "domains": {
                "user_feedback": [
                    {
                        "question": "how many actors",
                        "sql": "SELECT COUNT(*) FROM actor;",
                        "pattern": "user_corrected",
                        "tables": ["actor"],
                    }
                ]
            }
        }),
        encoding="utf-8",
    )
    loader = FewShotLoader(feedback_path=str(feedback))
    domains = {ex.domain for ex in loader.all_examples}
    assert "user_feedback" in domains


def test_loader_missing_feedback_file_does_not_raise(tmp_path):
    loader = FewShotLoader(feedback_path=str(tmp_path / "nope.yaml"))
    assert isinstance(loader.all_examples, list)
