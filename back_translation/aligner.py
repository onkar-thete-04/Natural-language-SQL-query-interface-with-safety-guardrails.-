from __future__ import annotations

import json

from relevance_filter.embedder import SchemaEmbedder
from shared.config import Settings
from shared.llm_client import LLMClient
from shared.text_similarity import cosine_similarity
from back_translation.models import AlignmentResult

JUDGE_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "score_alignment",
        "description": "Score semantic alignment between two questions.",
        "parameters": {
            "type": "object",
            "properties": {
                "score": {"type": "number", "description": "0.0-1.0 semantic equivalence"},
                "rationale": {"type": "string", "description": "Why this score"},
            },
            "required": ["score", "rationale"],
        },
    },
}


def align(
    original_question: str,
    back_translated_question: str,
    embedder: SchemaEmbedder,
    client: LLMClient,
    settings: Settings,
) -> AlignmentResult:
    sim = cosine_similarity(
        embedder.embed_single(original_question),
        embedder.embed_single(back_translated_question),
    )

    if sim >= settings.back_translation_embed_pass_threshold:
        return AlignmentResult(
            back_translated_question=back_translated_question,
            alignment_score=sim,
            method="embedding",
            judge_rationale=None,
            aligned=True,
            low_confidence=False,
        )

    if sim <= settings.back_translation_embed_fail_threshold:
        return AlignmentResult(
            back_translated_question=back_translated_question,
            alignment_score=sim,
            method="embedding",
            judge_rationale=None,
            aligned=False,
            low_confidence=True,
        )

    score, rationale = _judge(original_question, back_translated_question, client, settings)
    return AlignmentResult(
        back_translated_question=back_translated_question,
        alignment_score=score,
        method="llm_judge",
        judge_rationale=rationale,
        aligned=score >= 0.5,
        low_confidence=score < 0.5,
    )


def _judge(original: str, back_translated: str, client: LLMClient, settings: Settings) -> tuple[float, str]:
    prompt = (
        "On a scale of 0 to 1, how equivalent is Question A to Question B? "
        "A high score means the same intent; a low score means divergence.\n\n"
        f"Question A: {original}\nQuestion B: {back_translated}"
    )
    response = client.generate_sql_structured(
        prompt=prompt,
        tools=[JUDGE_TOOL_SCHEMA],
        tool_choice="required",
        model=settings.judge_model,
    )
    args = json.loads(response.choices[0].message.tool_calls[0].function.arguments)
    score = float(args["score"])
    score = max(0.0, min(1.0, score))
    return score, str(args["rationale"])
