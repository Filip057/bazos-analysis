# Bazos Car Analysis

## Project Overview

Web application for scraping, analyzing, and comparing used car listings from bazos.cz.
The goal is to help non-experts evaluate whether a car offer is fairly priced by providing
data-driven insights — price comparisons, market statistics, and anomaly detection.

## Tech Stack

- **Language**: Python 3.x
- **Web framework**: Flask + Flask-RESTful (API resources) + Jinja2 templates
- **Database**: MySQL (SQLAlchemy ORM for sync access, aiomysql for async scraper ops — some DB modules use a hybrid approach)
- **Scraping**: aiohttp + BeautifulSoup4 (async scraping pipeline)
- **ML/NLP**: spaCy (custom NER model for extracting vehicle attributes from listing descriptions)
- **Dependencies**: managed via Pipfile (pipenv) + requirements.txt
- **Environment config**: python-dotenv (.env file)

## Project Structure

```
bazos-analysis/
├── car_ner_model/         # Trained spaCy NER model (DO NOT modify without approval)
├── database/              # SQLAlchemy models (Brand, Model, Offer, Car view)
├── docs/                  # ML training philosophy, production guide, quick reference
├── labeling/              # Data labeling scripts for NER training data
├── migrations/            # DB migrations (SQL + Python) — NEVER overwrite existing
├── ml/                    # ML pipeline (extractor, resolvers, training, error analysis)
├── ml_models/             # Saved ML model artifacts (DO NOT modify without approval)
├── pipeline/              # Pipeline runner + checkpointing
├── pipeline_checkpoints/  # Saved pipeline state (runtime artifacts)
├── scraper/               # Async web scraper (data_scrap.py, car_models.py, database_operations.py, training_scraper.py)
├── scripts/               # Utility scripts (analysis, data quality, extraction, fixes)
├── tests/                 # Test suite
├── training_reports/      # Model retraining reports
├── utils/                 # Utilities (health check, labeling status, DB populate)
├── webapp/                # Flask app (app.py, config, static/, templates/)
└── Root files             # Config, docs, training data JSON, analysis CSVs
```

## Database Schema

Three normalized tables + one view for API compatibility:

- **brands** — car brand names (id, name)
- **models** — car models per brand (id, brand_id, name)
- **offers** — individual listings with extracted attributes:
  - Core: unique_id, model_id, year_manufacture, mileage, power, fuel, price, url, scraped_at
  - Derived: years_in_usage, price_per_km, mileage_per_year
  - Fuel values: `diesel`, `benzín`, `lpg`, `elektro`, `cng`, `hybrid`
- **car_view** — flattened read-only view joining brands + models + offers (used by Flask API)

## Code Conventions

- **Language**: All code, comments, docstrings, commit messages, and variable names in **English**
- **Type hints**: Required on all function signatures
- **Docstrings**: Required on all public functions and classes
- **Tests**: Every new feature or bugfix must include corresponding tests. Write tests FIRST, then implement.
- **Logging**: Use Python's `logging` module, not print statements

## Critical Rules — DO NOT Violate

1. **Never modify ML models** (`car_ner_model/`, `ml_models/`) without explicit user approval.
   Ask first, explain what you want to change and why.
2. **Never overwrite or edit existing migration files** in `migrations/`.
   Always create new migration files for schema changes.
3. **Test-first development**: Write or update tests before implementing changes.
4. **No direct DB writes in Flask routes** — use the database layer in `database/`.
5. **Async in scraper/ directory**: Code in `scraper/` must use aiohttp/aiomysql — never synchronous requests or mysql-connector there. Utility scripts in `scripts/` may use synchronous libraries where appropriate.

## Development Setup

- Local development only (no containers yet, Docker planned for future)
- Flask dev server: `python -m webapp.app` or similar
- Database: local MySQL instance
- Environment variables in `.env` (DB credentials, config)

## Future Plans

- Docker/docker-compose containerization
- Redis + Celery for scheduled tasks (periodic DB refresh, watchdog alerts)
- Watchdog feature: monitor specific offers and send notifications on price changes
