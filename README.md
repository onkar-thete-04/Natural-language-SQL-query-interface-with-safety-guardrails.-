# Text-to-SQL

Natural language to SQL pipeline for PostgreSQL. Takes a plain-English question, introspects the database schema, filters to relevant tables, detects ambiguous interpretations, assembles a context-rich prompt with few-shot examples, generates a SQL query via an LLM, validates it through a guardrail, safely executes it inside a read-only sandbox, and then scores the result for hallucination risk via back-translation alignment, sanity checks, multi-query validation, and weighted confidence aggregation.

## Architecture

```
User Question
     |
     |-- relevance_filter/     -> scores tables by semantic similarity (fastembed)
     |
     `-- ambiguity_resolver/   -> detects multi-interpretation questions, surfaces
     |                            structured ClarificationRequest or passes through
     |
     v
prompt_builder/                -> assembles final prompt from:
  |-- schema_engine/           ->   introspected schema (SQLAlchemy, cached at startup)
  |-- few_shot_loader.py       ->   curated question->SQL pairs (table-overlap selection)
  `-- relevance_filter output  ->   filtered table context
     |
     v
sql_generator/                 -> LLM function call -> structured SQL result
     |                         (sqlparse validation + retry). Emits SQL plus
     |                         explanation, confidence, tables, columns.
     |
     |-- back_translation/     -> translates SQL back into a natural-language question
     |                            and aligns it against the original (embedding + LLM
     |                            judge) to detect hallucinated SQL.
     |
     `-- multi_query/          -> detects complex questions and generates a second,
                                  independent SQL approach for cross-validation.
     v
guardrail/                     -> 5 rules: block DDL, block DML writes, row-limit
     |                         enforcement (default 1000), subquery depth (max 3),
     |                         EXPLAIN scan-cost limit (max 100k rows).
     v
sandbox/                       -> read-only engine + BEGIN READ ONLY ... ROLLBACK
     |                         transaction.
     v
executor/                      -> runs the guarded SQL, captures rows as list[dict],
     |                            EXPLAIN plan, execution time, truncation flag.
     |
     |-- sanity_check/         -> post-execution sanity checks: NULL-cell share,
     |                            empty-result anomaly detection, column/row checks.
     |
     |-- multi_query/          -> compares primary vs. alternative result sets
     |                            (row-level agreement) when a second approach ran.
     |
     `-- confidence/           -> weighted aggregation of syntax, alignment, sanity,
                                  agreement, and coverage into a 0-100 score.
     v
confidence report              -> emits a CONFIDENCE block; optionally blocks execution
                                when the score falls below the configured floor.
```

Three layers of defense keep generated SQL read-only: the app-level guardrail, a `BEGIN READ ONLY` transaction, and a SELECT-only DB user (`readonly_user`).

Each service is an independent package communicating through `shared/` only -- no cross-service imports.

## Tech Stack

- **Python** 3.11+
- **SQLAlchemy** 2.x -- schema introspection + read-only execution engine
- **fastembed** (ONNX, `BAAI/bge-small-en-v1.5`) -- table relevance embeddings
- **OpenAI SDK** -- LLM calls (pointed at NVIDIA API gateway)
- **sqlparse** >=0.5 -- SQL parsing for guardrail validation
- **FastAPI** + **Uvicorn** -- HTTP API (`api/`) exposing query/execute/schema/history/feedback endpoints
- **Streamlit** -- interactive frontend (`frontend/`)
- **httpx** -- async HTTP client (API testing + frontend-API transport)
- **PostgreSQL** 13 -- target database (Pagila sample schema)
- **Docker Compose** -- local database provisioning

## Project Structure

```
Text-to-SQL/
|-- shared/                  # Config, LLM client, shared models, errors
|-- schema_engine/           # SQLAlchemy introspection + sample extraction
|-- relevance_filter/        # fastembed-based table scoring
|-- ambiguity_resolver/      # Multi-interpretation detection
|-- prompt_builder/          # Prompt assembly + schema renderer
|-- sql_generator/           # LLM function call + sqlparse validation + retry
|-- guardrail/               # 5-rule SQL safety validator
|-- sandbox/                 # Read-only engine + BEGIN READ ONLY / ROLLBACK
|-- executor/                # Runs guarded SQL, returns rows + EXPLAIN + timing
|-- back_translation/        # SQL -> NL back-translation + alignment scoring
|-- sanity_check/            # Post-execution sanity checks + empty-result detection
|-- multi_query/             # Complexity detection + alternative generation + comparison
|-- confidence/              # Weighted confidence aggregation + schema coverage
|-- pipeline/                # End-to-end pipeline orchestration
|-- api/                     # FastAPI HTTP API (query, execute, schema, history, feedback)
|-- store/                   # SQLite query history + feedback persistence
|-- eval/                    # Evaluation harness + regression test cases
|-- frontend/                # Streamlit UI
|-- main.py                  # CLI entry point (pipeline steps [1]-[14])
|-- few_shot_examples.yaml   # Hand-curated question->SQL pairs
|-- few_shot_loader.py       # Example loader with table-overlap selector
|-- pyproject.toml           # Dependencies and project metadata
|-- docker-compose.yml       # PostgreSQL + Pagila + readonly_user provisioning
|-- Dockerfile               # App container
`-- Pagila_database/         # Pagila schema, seed data, readonly_user script, CSVs
```

## Setup

### 1. Install dependencies

```bash
pip install -e ".[dev]"
```

### 2. Configure environment

Copy or create `.env` at the project root:

```env
NVIDIA_API_KEY=your_key_here
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
SQL_GEN_MODEL=z-ai/glm-5.2
JUDGE_MODEL=minimaxai/minimax-m3
DATABASE_URL=postgresql://postgres:123456@localhost:5432/pagila
READONLY_DATABASE_URL=postgresql://readonly_user:readonly_pass@localhost:5432/pagila
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
```

All Phase 2 guardrail knobs are optional with sensible defaults -- add them only to override:

```env
BLOCK_DDL=true               # block DDL statements (default true)
BLOCK_DML_WRITES=true        # block INSERT/UPDATE/DELETE/MERGE (default true)
ENFORCE_ROW_LIMIT=1000       # cap rows returned; rewrites missing LIMIT (default 1000)
MAX_SUBQUERY_DEPTH=3         # max nested subquery depth (default 3)
MAX_SCAN_ROWS=100000         # max estimated EXPLAIN scan rows (default 100000)
```

Phase 3 (hallucination detection) adds four sub-phases on top of the Phase 1/2 pipeline, all driven through the `judge_model` where LLM input is needed:

- **Back-translation alignment** -- `back_translation/` translates the generated SQL back into a natural-language question and aligns it against the original question using embedding similarity plus an LLM judge. A low alignment score flags SQL that may not answer what was asked.
- **Sanity checks** -- `sanity_check/` inspects execution results for structural anomalies: excessive NULL cells, suspiciously empty result sets, and mismatched rows/columns.
- **Multi-query validation** -- `multi_query/` detects complex questions, generates a second independent SQL approach, executes it, and compares the two result sets for row-level agreement.
- **Confidence scoring** -- `confidence/` aggregates the five signals (SQL syntax, back-translation alignment, sanity checks, multi-query agreement, schema coverage) into a weighted 0-100 score and optionally blocks execution below a floor.

Phase 3 introduces these new pipeline steps: `[7]` back-translation alignment, `[8]` multi-query complexity check, `[12]` sanity checks, `[13]` multi-query comparison, and `[14]` confidence scoring.

Phase 3 knobs are optional with sensible defaults:

```env
BACK_TRANSLATION_EMBED_PASS_THRESHOLD=0.92  # embedding alignment -> aligned (default 0.92)
BACK_TRANSLATION_EMBED_FAIL_THRESHOLD=0.70  # embedding alignment -> low confidence (default 0.70)
SANITY_NULL_THRESHOLD=0.80                  # max allowed NULL-cell share (default 0.80)
BLOCK_ON_LOW_CONFIDENCE=false               # abort below MIN_CONFIDENCE_SCORE (default false)
MIN_CONFIDENCE_SCORE=60.0                   # confidence floor when blocking is on (default 60.0)
CONFIDENCE_WEIGHT_SYNTAX=0.10               # weight of the sql_syntax signal (default 0.10)
CONFIDENCE_WEIGHT_ALIGNMENT=0.30            # weight of the alignment signal (default 0.30)
CONFIDENCE_WEIGHT_SANITY=0.25               # weight of the sanity signal (default 0.25)
CONFIDENCE_WEIGHT_AGREEMENT=0.20            # weight of the agreement signal (default 0.20)
CONFIDENCE_WEIGHT_COVERAGE=0.15             # weight of the coverage signal (default 0.15)
```

> **Note -- NVIDIA NIM account limitations (Phase 3):** The LLM-driven Phase 3 steps (`back_translation`, the alignment LLM judge, multi-query alternative generation, and the empty-result judge) depend on the NVIDIA NIM API. The NIM free tier provides a baseline of 1,000 inference credits and a 40 requests/minute rate limit, and **model availability varies by account** -- a model listed in the NIM catalog may not be provisioned for your API key, in which case requests hang or return `404 "Not found for account"`. At the time of writing, `minimaxai/minimax-m3` is the model confirmed working for this project, while the `deepseek-ai/deepseek-v4-*` models were observed to hang. As a result, back-translation and multi-query may fail with `429 Too Many Requests` under rapid calls, or hang when the account quota is exhausted. These steps are advisory-by-default, so the pipeline still generates SQL, executes it, and scores confidence even when they fail.

Phase 4 (API + frontend + feedback loop) adds:

- **HTTP API** -- `api/` exposes `POST /v1/query`, `POST /v1/execute`, `GET /v1/schema`, `GET /v1/history`, `GET /v1/query/{id}`, and `POST /v1/feedback` via FastAPI. Start with `uvicorn api.app:create_app --factory --host 127.0.0.1 --port 8000` (auto docs at `/docs`).
- **Streamlit frontend** -- `frontend/app.py` (`streamlit run frontend/app.py`) with a question box, syntax-highlighted editable SQL, sortable results, confidence breakdown, and a history sidebar.
- **SQLite store** -- `store/` persists query history and feedback in `store/text_to_sql.db`.
- **Feedback flywheel** -- marking a result correct appends it to `few_shot_feedback.yaml` (merged into few-shot selection); marking it incorrect exports a regression case to `eval/test_cases.yaml`, runnable with `python -m eval.runner`.

Phase 4 knobs are optional with sensible defaults:

```env
SQLITE_DB_PATH=store/text_to_sql.db
FEW_SHOT_FEEDBACK_PATH=few_shot_feedback.yaml
EVAL_TEST_CASES_PATH=eval/test_cases.yaml
API_HOST=127.0.0.1
API_PORT=8000
API_BASE_URL=http://127.0.0.1:8000
```

## Evaluation

> 0.0% execution accuracy, 0.0% hallucination detection rate, zero unsafe queries executed across 0 test cases.

The evaluation suite measures the system against a 54-case golden dataset
(`evaluation/golden_dataset.yaml`) spanning six categories: simple lookups,
multi-table JOINs, GROUP BY aggregations, date-range filters, ambiguous
phrasing, and questions the database cannot answer. Four metrics are reported:

- **SQL exact match** -- normalized (sqlparse) string equivalence of generated vs gold SQL.
- **Execution match** -- generated result set equals gold SQL result set (order-insensitive).
- **Hallucination detection rate** -- recall over known-bad answers the system correctly flags.
- **Guardrail effectiveness** -- dangerous SQL blocked (see `evaluation/guardrail_cases.yaml`).

> **Known limitation:** the guardrail currently inspects only the first SQL
> statement, so multi-statement input such as `SELECT 1; DROP TABLE customer;`
> is not blocked. Until the guardrail rules are updated, the "unsafe queries
> executed" count may be non-zero.

Run live (requires NIM + seeded Postgres):

```bash
python -m evaluation
```

Run offline (scripted LLM, no NIM; still needs Postgres):

```bash
python -m evaluation --offline
```

The full stack (Postgres + API + frontend):

```bash
docker-compose up
```

After a live run, replace the headline line above with the real numbers
(`evaluation/report.json`).

### 3. Start PostgreSQL with Pagila

```bash
docker-compose up -d
```

This provisions a PostgreSQL 13.2 container with the full Pagila sample database plus a SELECT-only `readonly_user` (auto-created from `Pagila_database/03_create_readonly_user.sql`, which is mounted into the container's init directory). The init scripts only run on a fresh data volume -- if the container already exists, restart it to apply the readonly user:

```bash
docker-compose down -v && docker-compose up -d   # fresh volume -> reprovisions
```

### 4. Verify

```bash
python -m pytest -v
```

This runs the full suite across all packages (shared, schema_engine, relevance_filter, ambiguity_resolver, prompt_builder, sql_generator, guardrail, sandbox, executor, back_translation, sanity_check, multi_query, confidence), using the `testpaths` configured in `pyproject.toml`.

## Usage

```bash
python main.py "list all customers from Canada"
```

The pipeline outputs:

1. Introspected table count
2. Enriched schema with sample values
3. Relevant tables (filtered by semantic similarity)
4. Ambiguity detection results (if any)
5. Assembled prompt (system instructions + schema + examples + question)
6. Generated SQL (structured output: SQL + explanation + confidence + tables + columns)
7. Back-translation alignment (back-translated question + alignment score)
8. Multi-query complexity check (second approach when complex)
9. Guardrail result (all checks passed, or blocked with the offending rule)
10. Sandbox session opened (read-only)
11. Execution results (row count, columns, execution time, truncated flag, EXPLAIN plan)
12. Sanity checks (passed/total + anomalies)
13. Multi-query comparison (agreement between primary and alternative results)
14. Confidence report (weighted 0-100 score + per-signal bars + flags)

### Example

```
$ python main.py "which store generated the most revenue"

Question: which store generated the most revenue
----------------------------------------------------------
DB: postgresql://postgres:123456@localhost:5432/pagila
Model: z-ai/glm-5.2

[1] Introspecting schema...
    Found 21 tables
    Enriched with sample values

[2] Loading embedder...
    Model: BAAI/bge-small-en-v1.5

[3] Filtering relevant tables...
    Relevant tables: ['payment', 'staff', 'store']

[4] Checking for ambiguity...
    No ambiguity detected.

[5] Building prompt...
    Prompt length: 2156 characters

[6] Calling LLM (structured output)...
============================================================
GENERATED SQL
============================================================
SELECT s.store_id, SUM(p.amount) AS revenue
FROM payment p
JOIN staff st ON p.staff_id = st.staff_id
JOIN store s ON st.store_id = s.store_id
GROUP BY s.store_id
ORDER BY revenue DESC LIMIT 1;
============================================================

Explanation: Sums payment.amount per store, orders by revenue desc, top 1.
Confidence:  0.92
Tables:      ['payment', 'staff', 'store']
Columns:     ['store_id', 'revenue']

[7] Back-translating SQL -> question...
    Back-translated: Which store generated the highest total revenue?
    Alignment: 0.94 (embedding+judge)

[8] Checking multi-query complexity...
    Simple question -- skipping second approach

[9] Running guardrail checks...
    All guardrail checks passed.

[10] Opening sandbox session (read-only)...

[11] Executing query...
============================================================
EXECUTION RESULTS
============================================================
Row count:         1
Execution time:    12.34 ms
Truncated:         False
Columns:           ['store_id', 'revenue']

Preview (first 5 rows):
  0: {'store_id': 2, 'revenue': 34099.73}

EXPLAIN plan:
Limit  (cost=47.18..47.18 rows=1 width=12)
  ->  Sort  (cost=47.18..47.18 rows=2 width=12)
        ->  HashAggregate  (...)
============================================================

[12] Running sanity checks...
    5/5 checks passed

[13] Comparing multi-query results...
    Skipped (no second approach)

[14] Computing confidence...
============================================================
CONFIDENCE: 92.6 / 100
============================================================
  sql_syntax                    1.00  ####################
  back_translation_alignment    0.94  ###################
  sanity_checks                 1.00  ####################
  schema_coverage               1.00  ####################
============================================================
```

## Testing

```bash
python -m pytest -v
```
