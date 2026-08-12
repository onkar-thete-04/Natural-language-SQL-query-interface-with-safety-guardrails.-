# Text-to-SQL

Natural language to SQL pipeline for PostgreSQL. Takes a plain-English question, introspects the database schema, filters to relevant tables, detects ambiguous interpretations, assembles a context-rich prompt with few-shot examples, generates a SQL query via an LLM, validates it through a guardrail, and safely executes it inside a read-only sandbox.

## Architecture

```
User Question
     │
     ├── relevance_filter/     → scores tables by semantic similarity (fastembed)
     │
     └── ambiguity_resolver/   → detects multi-interpretation questions, surfaces
     │                            structured ClarificationRequest or passes through
     │
     ▼
prompt_builder/                → assembles final prompt from:
  ├── schema_engine/           →   introspected schema (SQLAlchemy, cached at startup)
  ├── few_shot_loader.py       →   curated question→SQL pairs (table-overlap selection)
  └── relevance_filter output  →   filtered table context
     │
     ▼
sql_generator/                 → LLM function call → structured SQL result
     │                         (sqlparse validation + retry). Emits SQL plus
     │                         explanation, confidence, tables, columns.
     ▼
guardrail/                     → 5 rules: block DDL, block DML writes, row-limit
     │                         enforcement (default 1000), subquery depth (max 3),
     │                         EXPLAIN scan-cost limit (max 100k rows).
     ▼
sandbox/                       → read-only engine + BEGIN READ ONLY … ROLLBACK
     │                         transaction.
     ▼
executor/                      → runs the guarded SQL, captures rows as list[dict],
                               EXPLAIN plan, execution time, truncation flag.
```

Three layers of defense keep generated SQL read-only: the app-level guardrail, a `BEGIN READ ONLY` transaction, and a SELECT-only DB user (`readonly_user`).

Each service is an independent package communicating through `shared/` only — no cross-service imports.

## Tech Stack

- **Python** 3.11+
- **SQLAlchemy** 2.x — schema introspection + read-only execution engine
- **fastembed** (ONNX, `BAAI/bge-small-en-v1.5`) — table relevance embeddings
- **OpenAI SDK** — LLM calls (pointed at NVIDIA API gateway)
- **sqlparse** >=0.5 — SQL parsing for guardrail validation
- **PostgreSQL** 13 — target database (Pagila sample schema)
- **Docker Compose** — local database provisioning

## Project Structure

```
Text-to-SQL/
├── shared/                  # Config, LLM client, shared models, errors
├── schema_engine/           # SQLAlchemy introspection + sample extraction
├── relevance_filter/        # fastembed-based table scoring
├── ambiguity_resolver/      # Multi-interpretation detection
├── prompt_builder/          # Prompt assembly + schema renderer
├── sql_generator/           # LLM function call + sqlparse validation + retry
├── guardrail/               # 5-rule SQL safety validator
├── sandbox/                 # Read-only engine + BEGIN READ ONLY / ROLLBACK
├── executor/                # Runs guarded SQL, returns rows + EXPLAIN + timing
├── main.py                  # CLI entry point (pipeline steps [1]-[9])
├── few_shot_examples.yaml   # Hand-curated question→SQL pairs
├── few_shot_loader.py       # Example loader with table-overlap selector
├── pyproject.toml           # Dependencies and project metadata
├── docker-compose.yml       # PostgreSQL + Pagila + readonly_user provisioning
├── Dockerfile               # App container
└── Pagila_database/         # Pagila schema, seed data, readonly_user script, CSVs
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
SQL_GEN_MODEL=deepseek-ai/deepseek-v4-flash
JUDGE_MODEL=deepseek-ai/deepseek-v4-pro
DATABASE_URL=postgresql://postgres:123456@localhost:5432/pagila
READONLY_DATABASE_URL=postgresql://readonly_user:readonly_pass@localhost:5432/pagila
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
```

All Phase 2 guardrail knobs are optional with sensible defaults — add them only to override:

```env
BLOCK_DDL=true               # block DDL statements (default true)
BLOCK_DML_WRITES=true        # block INSERT/UPDATE/DELETE/MERGE (default true)
ENFORCE_ROW_LIMIT=1000       # cap rows returned; rewrites missing LIMIT (default 1000)
MAX_SUBQUERY_DEPTH=3         # max nested subquery depth (default 3)
MAX_SCAN_ROWS=100000         # max estimated EXPLAIN scan rows (default 100000)
```

### 3. Start PostgreSQL with Pagila

```bash
docker-compose up -d
```

This provisions a PostgreSQL 13.2 container with the full Pagila sample database plus a SELECT-only `readonly_user` (auto-created from `Pagila_database/03_create_readonly_user.sql`, which is mounted into the container's init directory). The init scripts only run on a fresh data volume — if the container already exists, restart it to apply the readonly user:

```bash
docker-compose down -v && docker-compose up -d   # fresh volume → reprovisions
```

### 4. Verify

```bash
python -m pytest schema_engine/tests/ relevance_filter/tests/ ambiguity_resolver/tests/ prompt_builder/tests/ sql_generator/tests/ guardrail/tests/ sandbox/tests/ executor/tests/ -v
```

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
7. Guardrail result (all checks passed, or blocked with the offending rule)
8. Sandbox session opened (read-only)
9. Execution results (row count, columns, execution time, truncated flag, EXPLAIN plan)

### Example

```
$ python main.py "which store generated the most revenue"

Question: which store generated the most revenue
----------------------------------------------------------
DB: postgresql://postgres:123456@localhost:5432/pagila
Model: deepseek-ai/deepseek-v4-flash

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

[7] Running guardrail checks...
    All guardrail checks passed.

[8] Opening sandbox session (read-only)...

[9] Executing query...
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
```

## Testing

```bash
python -m pytest schema_engine/tests/ relevance_filter/tests/ ambiguity_resolver/tests/ prompt_builder/tests/ sql_generator/tests/ guardrail/tests/ sandbox/tests/ executor/tests/ -v
```
