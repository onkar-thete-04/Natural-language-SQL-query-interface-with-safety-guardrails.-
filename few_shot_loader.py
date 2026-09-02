"""
few_shot_loader.py

Loads curated question -> SQL few-shot examples and selects the most
relevant subset for a given question, for injection into the NL-to-SQL
prompt (Phase 1.2).

Design decisions:
- Examples are hand-curated (see few_shot_examples.yaml), never
  auto-generated. A wrong example silently teaches the generator to
  repeat the same mistake on every future query that resembles it.
- Selection is done by table-overlap scoring against the relevant tables
  already identified by the Phase 1.3 schema relevance filter. This adds
  zero extra embedding/LLM calls -- it reuses work already done upstream.
- Organized by "domain" in the YAML file so new curated sets (e.g. for
  AdventureWorks later) can be added without touching this loader.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_EXAMPLES_PATH = Path(__file__).parent / "few_shot_examples.yaml"
DEFAULT_FEEDBACK_PATH = Path(__file__).parent / "few_shot_feedback.yaml"
DEFAULT_TOP_N = 4


@dataclass(frozen=True)
class FewShotExample:
    question: str
    sql: str
    pattern: str
    tables: tuple[str, ...]
    domain: str

    def as_prompt_block(self) -> str:
        """Render as a Question/SQL pair block ready for prompt injection."""
        return f"Question: {self.question}\nSQL: {self.sql.strip()}"


class FewShotLoader:
    """Loads curated few-shot examples and selects the best subset per question."""

    def __init__(
        self,
        examples_path: str | Path = DEFAULT_EXAMPLES_PATH,
        feedback_path: str | Path = DEFAULT_FEEDBACK_PATH,
    ):
        self.examples_path = Path(examples_path)
        self.feedback_path = Path(feedback_path)
        self._examples: list[FewShotExample] = []
        self._load()
        self._load_feedback()

    def _load(self) -> None:
        if not self.examples_path.exists():
            raise FileNotFoundError(
                f"Few-shot examples file not found: {self.examples_path}"
            )
        with open(self.examples_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        examples = self._parse_domains(raw)
        if not examples:
            raise ValueError(f"No few-shot examples found in {self.examples_path}")
        self._examples = examples

    def _load_feedback(self) -> None:
        if not self.feedback_path.exists():
            return
        try:
            with open(self.feedback_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
        except Exception:
            return
        self._examples.extend(self._parse_domains(raw))

    def _parse_domains(self, raw) -> list[FewShotExample]:
        domains = raw.get("domains", {}) or {}
        examples: list[FewShotExample] = []
        for domain_name, domain_examples in domains.items():
            for item in domain_examples or []:
                examples.append(
                    FewShotExample(
                        question=item["question"],
                        sql=item["sql"],
                        pattern=item.get("pattern", "unspecified"),
                        tables=tuple(t.lower() for t in item.get("tables", [])),
                        domain=domain_name,
                    )
                )
        return examples

    @property
    def all_examples(self) -> list[FewShotExample]:
        return list(self._examples)

    def select(
        self,
        relevant_tables: list[str] | None = None,
        top_n: int = DEFAULT_TOP_N,
    ) -> list[FewShotExample]:
        """
        Select the top_n most relevant examples for the current question.

        If relevant_tables is provided (typically the output of the
        Phase 1.3 schema relevance filter), examples are ranked by how
        many of their tables overlap with it, so the model sees patterns
        that match what it's about to write SQL against.

        Falls back to one example per distinct pattern if no table
        context is given, or if overlap alone doesn't fill top_n.
        """
        if not relevant_tables:
            return self._diverse_default(top_n)

        relevant_set = {t.lower() for t in relevant_tables}

        scored = [
            (len(relevant_set & set(ex.tables)), ex) for ex in self._examples
        ]
        scored.sort(key=lambda pair: pair[0], reverse=True)

        selected = [ex for score, ex in scored if score > 0][:top_n]

        if len(selected) < top_n:
            backfill = [ex for ex in self._diverse_default(top_n) if ex not in selected]
            selected += backfill[: top_n - len(selected)]

        return selected[:top_n]

    def _diverse_default(self, top_n: int) -> list[FewShotExample]:
        """One example per distinct pattern, up to top_n -- a sane fallback
        when there's no table context to score against."""
        seen_patterns: set[str] = set()
        diverse: list[FewShotExample] = []
        for ex in self._examples:
            if ex.pattern not in seen_patterns:
                diverse.append(ex)
                seen_patterns.add(ex.pattern)
            if len(diverse) >= top_n:
                break
        return diverse


def render_few_shot_block(examples: list[FewShotExample]) -> str:
    """Render selected examples as a single string ready for prompt injection."""
    return "\n\n".join(ex.as_prompt_block() for ex in examples)


if __name__ == "__main__":
    loader = FewShotLoader()
    print(f"Loaded {len(loader.all_examples)} total examples\n")

    # Simulates the prompt constructor calling this after Phase 1.3's
    # schema filter has already identified relevant tables for a
    # "revenue by store" style question.
    relevant = ["payment", "staff", "store"]
    selected = loader.select(relevant_tables=relevant, top_n=4)

    print(f"Selected {len(selected)} examples for relevant_tables={relevant}:\n")
    print(render_few_shot_block(selected))
    print(f"\nPatterns selected: {[ex.pattern for ex in selected]}")
