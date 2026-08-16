from __future__ import annotations

import csv
import time
from pathlib import Path

OUT = Path(__file__).parent / "backtranslation_tuning.csv"

# (question, sql, label) — aligned = correct SQL, diverged = wrong SQL.
# No SQL generation needed: pairs are hand-curated so we KNOW the ground truth.
CASES = [
    # ---- aligned (SQL correctly answers the question) ----
    ("What is the email address of the customer named Mary Smith?",
     "SELECT email FROM customer WHERE first_name = 'Mary' AND last_name = 'Smith';", "aligned"),
    ("Which films has actor Nick Wahlberg appeared in?",
     "SELECT f.title FROM film f JOIN film_actor fa ON f.film_id = fa.film_id JOIN actor a ON fa.actor_id = a.actor_id WHERE a.first_name = 'Nick' AND a.last_name = 'Wahlberg';", "aligned"),
    ("How many films are there in each rating category?",
     "SELECT rating, COUNT(*) FROM film GROUP BY rating;", "aligned"),
    ("List all customers from Canada.",
     "SELECT c.first_name, c.last_name FROM customer c JOIN address a ON c.address_id = a.address_id JOIN city ci ON a.city_id = ci.city_id JOIN country co ON ci.country_id = co.country_id WHERE co.country = 'Canada';", "aligned"),
    ("Which store generated the most revenue?",
     "SELECT s.store_id, SUM(p.amount) AS revenue FROM payment p JOIN staff st ON p.staff_id = st.staff_id JOIN store s ON st.store_id = s.store_id GROUP BY s.store_id ORDER BY revenue DESC LIMIT 1;", "aligned"),
    ("How many rentals were made in May 2005?",
     "SELECT COUNT(*) FROM rental WHERE rental_date >= '2005-05-01' AND rental_date < '2005-06-01';", "aligned"),

    # ---- diverged (SQL does NOT answer the question) ----
    # subtle: COUNT instead of SUM — same tables, wrong meaning
    ("Which store generated the most revenue?",
     "SELECT s.store_id, COUNT(p.payment_id) AS revenue FROM payment p JOIN staff st ON p.staff_id = st.staff_id JOIN store s ON st.store_id = s.store_id GROUP BY s.store_id ORDER BY revenue DESC LIMIT 1;", "diverged"),
    # blatant: answers a totally different question
    ("What is the email address of the customer named Mary Smith?",
     "SELECT title FROM film WHERE rating = 'G';", "diverged"),
    # subtle: missing GROUP BY — wrong result shape
    ("How many films are there in each rating category?",
     "SELECT COUNT(*) FROM film;", "diverged"),
    # subtle: wrong country filter
    ("List all customers from Canada.",
     "SELECT c.first_name, c.last_name FROM customer c JOIN address a ON c.address_id = a.address_id JOIN city ci ON a.city_id = ci.city_id JOIN country co ON ci.country_id = co.country_id WHERE co.country = 'Mexico';", "diverged"),
    # subtle: hardcoded wrong actor id
    ("Which films has actor Nick Wahlberg appeared in?",
     "SELECT f.title FROM film f JOIN film_actor fa ON f.film_id = fa.film_id WHERE fa.actor_id = 1;", "diverged"),
    # blatant: wrong table entirely
    ("How many rentals were made in May 2005?",
     "SELECT COUNT(*) FROM payment;", "diverged"),
]


def retry(func, *args, retries=4, base_delay=5, **kwargs):
    from shared.errors import LLMClientError
    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except LLMClientError as exc:
            delay = base_delay * (2 ** attempt)
            print(f"        retry ({attempt + 1}/{retries}), sleeping {delay}s...")
            time.sleep(delay)
    raise LLMClientError(f"gave up after {retries} retries")


def main() -> None:
    from shared.config import Settings
    from shared.llm_client import LLMClient
    from relevance_filter.embedder import SchemaEmbedder
    from shared.text_similarity import cosine_similarity

    settings = Settings()
    client = LLMClient(settings)
    embedder = SchemaEmbedder(settings.embedding_model)

    print(f"Back-translate model: {settings.sql_gen_model} (gen model — judge is flaky)")
    print(f"Embedding: {settings.embedding_model}")
    print(f"Pass threshold: {settings.back_translation_embed_pass_threshold}")
    print(f"Fail threshold: {settings.back_translation_embed_fail_threshold}")
    print("-" * 60)

    rows = []
    for i, (question, sql, label) in enumerate(CASES, 1):
        print(f"[{i}/{len(CASES)}] ({label}) {question}")

        back_translated = ""
        try:
            bt_prompt = (
                "Here is a SQL query:\n" + sql + "\n\n"
                "What question does this SQL query answer? "
                "Reply with a single natural-language question and nothing else."
            )
            back_translated = retry(client.generate_sql, bt_prompt, model=settings.sql_gen_model).strip()
            print(f"    Back: {back_translated[:90]}")
        except Exception as exc:
            print(f"    BACK-TRANSLATION FAILED: {exc}")

        score = 0.0
        if back_translated:
            score = cosine_similarity(
                embedder.embed_single(question),
                embedder.embed_single(back_translated),
            )
            print(f"    Similarity: {score:.4f}")

        rows.append({
            "label": label,
            "question": question,
            "sql": sql,
            "back_translated_question": back_translated,
            "embedding_similarity": round(score, 4),
        })
        time.sleep(10)

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "label", "question", "sql", "back_translated_question", "embedding_similarity",
        ])
        writer.writeheader()
        writer.writerows(rows)

    aligned = [r["embedding_similarity"] for r in rows if r["label"] == "aligned" and r["embedding_similarity"] > 0]
    diverged = [r["embedding_similarity"] for r in rows if r["label"] == "diverged" and r["embedding_similarity"] > 0]
    print("\n" + "=" * 60)
    print(f"Wrote {len(rows)} rows to {OUT}")
    if aligned:
        print(f"aligned similarities:   min {min(aligned):.3f} / max {max(aligned):.3f}")
    if diverged:
        print(f"diverged similarities:  min {min(diverged):.3f} / max {max(diverged):.3f}")


if __name__ == "__main__":
    main()
