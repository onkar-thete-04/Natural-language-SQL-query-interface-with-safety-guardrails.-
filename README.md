# Text-to-SQL

Natural language to SQL pipeline for PostgreSQL. Takes a plain-English question, introspects the database schema, filters to relevant tables, detects ambiguous interpretations, assembles a context-rich prompt with few-shot examples, and generates a SQL query via an LLM.

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
shared/llm_client              → calls NVIDIA API (OpenAI-compatible) for SQL gen
     │
     ▼
Generated SQL
```

Each service is an independent package communicating through `shared/` only — no cross-service imports.

## Tech Stack

- **Python** 3.11+
- **SQLAlchemy** 2.x — schema introspection
- **fastembed** (ONNX, `BAAI/bge-small-en-v1.5`) — table relevance embeddings
- **OpenAI SDK** — LLM calls (pointed at NVIDIA API gateway)
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
├── main.py                  # CLI entry point
├── few_shot_examples.yaml   # Hand-curated question→SQL pairs
├── few_shot_loader.py       # Example loader with table-overlap selector
├── pyproject.toml           # Dependencies and project metadata
├── docker-compose.yml       # PostgreSQL + Pagila provisioning
├── Dockerfile               # App container
└── Pagila_database/         # Pagila schema, seed data, CSVs
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
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
```

### 3. Start PostgreSQL with Pagila

```bash
docker-compose up -d
```

This provisions a PostgreSQL 13.2 container with the full Pagila sample database pre-loaded (schema + seed data).

### 4. Verify

```bash
python -m pytest schema_engine/tests/ relevance_filter/tests/ ambiguity_resolver/tests/ prompt_builder/tests/ -v
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
6. Generated SQL query

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
    AMBIGUITY DETECTED:
    [1] Gross Revenue: Total payments before subtracting refunds or adjustments
        Example: Find total revenue by store from payments
        Constraint: Use payment.amount AS revenue. Do not subtract refunds.

[5] Building prompt...
    Prompt length: 2156 characters

[6] Calling LLM...
======================================================
GENERATED SQL
======================================================
SELECT s.store_id, SUM(p.amount) AS revenue
FROM payment p
JOIN staff st ON p.staff_id = st.staff_id
JOIN store s ON st.store_id = s.store_id
GROUP BY s.store_id
ORDER BY revenue DESC LIMIT 1;
======================================================
```

## Testing

```bash
python -m pytest schema_engine/tests/ relevance_filter/tests/ ambiguity_resolver/tests/ prompt_builder/tests/ -v
```
