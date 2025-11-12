# Backend Data Models & Storage Surfaces (Quick Scan)

_Source: filenames under `backend/db/models` and `backend/db/migrations` – derived via quick scan._

## ORM Models

| Model File | Domain Aggregate | Storage Backend | Notes |
| --- | --- | --- | --- |
| `user.py` | Operator accounts, roles, API keys | PostgreSQL (`users` table) | Secured with bcrypt + JWT claims |
| `stock.py` | Master list of tickers + metadata | PostgreSQL | Primary key used by crawlers & analytics |
| `market_data.py` | Minute/daily OHLC data cache | PostgreSQL + Redis | Seeds analytics & charting |
| `news.py` | Crawled articles & metadata | PostgreSQL + Milvus vector IDs | Linked to embeddings for RAG |
| `prediction.py` | GPT-4o inference outputs | PostgreSQL | Includes probability & confidence bands |
| `model.py` | Registered AI model configs | PostgreSQL | Tracks prompt, temperature, provider |
| `model_evaluation.py` | Offline evaluation scores | PostgreSQL | Feeds `/evaluations` API |
| `evaluation_history.py` | Trend of evaluation metrics | PostgreSQL | Used for regression detection |
| `daily_performance.py` | Aggregated KPI snapshots | PostgreSQL | Surfaces on dashboard cards |
| `stock_analysis.py` | AI explanations per stock | PostgreSQL | Displayed in `stocks` route |
| `ab_test_config.py` | Experiment variants | PostgreSQL | Toggles alternative prompts |
| `match.py` | News-stock link table | PostgreSQL | Maintains relevance graph |

## Schema / Migration Inventory

`backend/db/migrations/` contains incremental DDL scripts. Key operations inferred from filenames:

- `add_minute_table.py`, `add_structured_price_fields.py` – extend market data granularity.
- `add_evaluation_tables.py`, `add_impact_analysis_fields.py` – support new analytics KPIs.
- `add_source_column.py`, `add_table_comments.py` – governance & lineage metadata.
- `remove_foreign_keys.py`, `remove_stock_code_unique_constraint.sql` – loosen constraints for brownfield imports.

## Vector & Search Assets

- `backend/db/milvus_client.py` manages Milvus connections for embeddings sourced from OpenAI `text-embedding-3-small`.
- Embedding IDs stored alongside `news` and `prediction` rows for RAG lookups.

## Data Governance To-Dos

- Confirm Alembic/Flyway tracking; migrations are Python scripts but no version table observed (consider standardizing).
- Add ER diagram export before production deployment to document FK relationships between `news`, `predictions`, and `evaluations`.
