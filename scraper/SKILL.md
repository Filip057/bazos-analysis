---
name: bazos-scraping
description: >
  Skill for building and maintaining the async web scraper that collects car listings
  from bazos.cz. Use this skill whenever working on scraping logic, adding new data
  sources or listing categories, fixing parsing issues, handling rate limiting or
  anti-bot measures, managing scraping pipelines and checkpoints, or debugging
  data collection problems. Also trigger when the user mentions bazos.cz URLs,
  aiohttp/BeautifulSoup code in the scraper/ directory, or pipeline orchestration.
---

# Bazos.cz Scraping Skill

## Purpose

Async scraping of car listings from bazos.cz — collecting offer URLs, downloading
listing pages, and parsing raw HTML into structured candidate data before ML extraction.

## Architecture

```
scraper/
├── data_scrap.py            # Main scraping logic (async aiohttp sessions, page parsing, URL construction, ML extraction integration)
├── car_models.py            # Brand/model definitions (MODEL_ALIASES, CAR_MODELS dicts)
├── database_operations.py   # DB operations for scraped data (hybrid sync/async)
├── training_scraper.py      # Standalone scraper for generating ML training data
└── __init__.py
```

Supporting modules:
- `pipeline/` — orchestrates scrape → extract → store workflow with checkpointing
- `pipeline_checkpoints/` — persisted pipeline state for resumable runs

## Key Technical Constraints

### Async-only
All network I/O must use `aiohttp` with `async/await`. Never use `requests` or other
synchronous HTTP libraries in scraping code. Database writes from the scraper use
`aiomysql`, not the synchronous `mysql-connector-python`.

### Rate Limiting & Politeness
- Respect bazos.cz by implementing delays between requests
- Current retry logic: exponential backoff (RETRY_DELAY * (attempt + 1)), 3 retries on any error
- No explicit User-Agent header set yet (uses aiohttp default) — consider adding one
- No specific HTTP 429 handling yet — retries cover it generically but dedicated 429 logic would be better
- No randomized jitter on delays yet — current intervals are deterministic

### Resilience
- The pipeline supports checkpointing — if a scrape is interrupted, it can resume
  from the last checkpoint rather than restarting
- Always handle network timeouts, malformed HTML, and missing fields gracefully
- Log warnings for unparseable listings rather than crashing the pipeline

### Data Flow

1. **URL construction**: `data_scrap.py` builds listing URLs per brand/model from bazos.cz URL patterns (brand/model defs from `car_models.py`)
2. **Page fetching**: Async download of listing pages (respect rate limits)
3. **HTML parsing**: BeautifulSoup4 extracts raw text fields (title, description, price, URL, unique_id)
4. **ML extraction (integrated)**: `data_scrap.py` directly calls `ProductionExtractor` from `ml.production_extractor` in `process_data()` to extract structured attributes (mileage, year, fuel, power) from description text
5. **Storage**: Fully enriched offers written to MySQL via SQLAlchemy/aiomysql

**Important**: ML extraction is integrated directly into the scraping process, not a separate
pipeline step. The `pipeline/runner.py` orchestrates this, but extraction happens inside
`data_scrap.py`'s `process_data()` function.

### ML Integration Boundary
- The scraper calls `ProductionExtractor` to extract attributes, but does NOT train or modify ML models
- If extraction accuracy is poor, the fix belongs in `ml/` (model retraining, resolver logic) — not in scraper code
- Never modify `ProductionExtractor` behavior from within scraper code

## Database Target

Scraped data ultimately lands in the `offers` table:
- `unique_id` — bazos.cz listing identifier (for deduplication)
- `model_id` — FK to models table (determined by which brand/model URL was scraped)
- `price` — parsed from listing
- `url` — full listing URL
- `scraped_at` — timestamp of scrape
- Attribute fields (year_manufacture, mileage, power, fuel) are populated during scraping via ML extraction

## Patterns to Follow

### Adding a New Scraping Target
1. Add brand/model definitions in `car_models.py` (MODEL_ALIASES, CAR_MODELS dicts)
2. Add/update URL construction and parser function in `data_scrap.py`
3. Write tests for the new parser with sample HTML
4. Test with a small batch before full scrape

### Fixing a Parsing Bug
1. Get a sample of the broken HTML (save to tests/ as fixture)
2. Write a failing test that reproduces the issue
3. Fix the parser
4. Verify against the fixture

### Modifying Pipeline Behavior
1. Check `pipeline/` for current orchestration logic
2. Ensure checkpoint compatibility — new changes must not break resume from old checkpoints
3. Test both fresh run and resume-from-checkpoint scenarios

## Common Pitfalls

- **bazos.cz HTML changes**: The site has no stable API. HTML structure can change without
  notice. When parsing breaks, check if the site's markup changed before debugging logic.
- **Encoding**: bazos.cz uses Czech text. Ensure UTF-8 handling throughout.
- **Duplicate offers**: Always check `unique_id` before inserting. Use upsert logic.
- **Large batch sizes**: When scraping all brands/models, memory can spike. Use streaming/batched
  inserts rather than collecting everything in memory.
