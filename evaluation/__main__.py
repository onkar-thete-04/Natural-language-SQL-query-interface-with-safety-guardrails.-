from __future__ import annotations

import argparse

from shared.config import Settings


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the evaluation suite")
    parser.add_argument("--offline", action="store_true", help="Use scripted LLM (no NIM)")
    args = parser.parse_args()

    from evaluation.runner import EvaluationRunner
    from evaluation.report import write_json, write_markdown

    settings = Settings()
    report = EvaluationRunner(settings, offline=args.offline).run()
    write_json(report, settings.eval_report_path)
    print(write_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
